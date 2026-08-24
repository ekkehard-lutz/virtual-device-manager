from collections.abc import Mapping

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import Event, HomeAssistant, State
from homeassistant.helpers import entity_registry
from homeassistant.helpers.entity import DeviceInfo

from .aggregator import SourceValue, aggregate_values
from .const import DOMAIN
from .device_class_metadata import get_device_class_metadata
from .lifecycle import virtual_entity_unique_id
from .models import VirtualDevice, VirtualEntity
from .source_manager import SourceManager


class VirtualDeviceSensor(SensorEntity):
    """Representation of a Virtual Device Manager virtual sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        device: VirtualDevice,
        entity: VirtualEntity,
    ) -> None:
        """Initialize the virtual sensor."""
        self._device = device
        self._virtual_entity = entity

        self._attr_unique_id = virtual_entity_unique_id(entity.id)

        self._attr_name = entity.device_class

        metadata = get_device_class_metadata(entity.device_class)
        self._attr_device_class = entity.device_class
        self._attr_native_unit_of_measurement = metadata.native_unit
        self._attr_state_class = metadata.state_class
        self._attr_native_value = None

    def update_value(
        self,
        values: list[SourceValue],
        write_state: bool = True,
    ) -> None:
        """Update the sensor value from source values."""
        self._attr_native_value = aggregate_values(
            values,
            self._virtual_entity.device_class,
            self._virtual_entity.aggregation,
        )

        if write_state:
            self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        """Return information about the virtual device."""
        return DeviceInfo(
            identifiers={
                ("virtual_device", self._device.id),
            },
        )


class VirtualSensorManager:
    """Manage virtual sensors at runtime."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor manager."""
        self._hass = hass
        self._config_entry = config_entry
        self._sensors: dict[str, VirtualDeviceSensor] = {}
        self._async_add_entities = None

    def initialize(
        self,
        async_add_entities,
    ) -> None:
        """Initialize the runtime entity registration."""
        self._async_add_entities = async_add_entities

    @property
    def sensors(self) -> Mapping[str, VirtualDeviceSensor]:
        """Return currently registered virtual sensors."""
        return self._sensors

    def register_existing(
        self,
        sensor: VirtualDeviceSensor,
    ) -> None:
        """Register an existing sensor."""
        registry = entity_registry.async_get(self._hass)

        registry_entry = registry.async_get_entity_id(
            "sensor",
            DOMAIN,
            sensor.unique_id,
        )

        if registry_entry is not None:
            entity = registry.async_get(registry_entry)

            if entity is not None:
                sensor._attr_name = entity.name

        self._sensors[sensor._virtual_entity.id] = sensor

    def add_entity(
        self,
        device: VirtualDevice,
        entity: VirtualEntity,
        values: list[SourceValue],
        name: str | None = None,
        device_id: str | None = None,
    ) -> None:
        """Create and add a virtual sensor to Home Assistant."""
        if self._async_add_entities is None:
            raise RuntimeError("VirtualSensorManager is not initialized")

        if entity.id in self._sensors:
            raise ValueError(f"Virtual sensor '{entity.id}' is already registered")

        sensor = VirtualDeviceSensor(
            device,
            entity,
        )

        registry = entity_registry.async_get(self._hass)

        create_kwargs = {
            "domain": "sensor",
            "platform": DOMAIN,
            "unique_id": sensor.unique_id,
            "config_entry": self._config_entry,
            "suggested_object_id": entity.id,
            "original_name": entity.device_class,
        }
        if device_id is not None:
            create_kwargs["device_id"] = device_id

        registry_entry = registry.async_get_or_create(
            **create_kwargs,
        )

        if name is not None and registry_entry.name != name:
            registry.async_update_entity(registry_entry.entity_id, name=name)

        sensor.update_value(
            values,
            write_state=False,
        )

        self._sensors[entity.id] = sensor

        self._async_add_entities([sensor])

    async def async_remove_entity(self, entity_id: str) -> None:
        """Remove one runtime virtual sensor if it is currently active."""
        sensor = self._sensors.pop(entity_id, None)

        if sensor is not None:
            await sensor.async_remove(force_remove=True)

    async def async_remove_entity_by_unique_id(self, unique_id: str) -> None:
        """Remove a runtime sensor by its stable Home Assistant unique ID."""
        for entity_id, sensor in list(self._sensors.items()):
            if sensor.unique_id == unique_id:
                await self.async_remove_entity(entity_id)
                return

    async def async_remove_entities_for_device(self, device_id: str) -> None:
        """Remove all active virtual sensors belonging to a device."""
        for entity_id, sensor in list(self._sensors.items()):
            if sensor._device.id == device_id:
                await self.async_remove_entity(entity_id)

    def update_entities(
        self,
        source_manager: SourceManager,
        entity_ids: list[str],
    ) -> None:
        """Update virtual sensors after source relationships changed."""
        for entity_id in entity_ids:
            sensor = self._sensors.get(entity_id)

            if sensor is None:
                continue

            sensor.update_value(
                source_manager.get_source_values(entity_id),
            )

    async def async_replace_entity(
        self,
        device: VirtualDevice,
        entity: VirtualEntity,
        values: list[SourceValue],
        name: str | None = None,
    ) -> None:
        """Replace a runtime sensor while retaining its registry unique ID."""
        await self.async_remove_entity(entity.id)
        self.add_entity(
            device,
            entity,
            values,
            name=name,
        )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Set up Virtual Device Manager virtual sensors."""
    entry_data = hass.data[DOMAIN][entry.entry_id]
    storage = entry_data["storage"]

    source_manager = entry_data["source_manager"]

    sensor_manager = entry_data["sensor_manager"]

    sensor_manager.initialize(
        async_add_entities,
    )

    entities: list[VirtualDeviceSensor] = []

    for device in storage.get_virtual_devices():
        source_manager.rebuild_virtual_device(
            hass,
            device,
        )

        for virtual_entity in device.entities:
            sensor = VirtualDeviceSensor(
                device,
                virtual_entity,
            )

            sensor.update_value(
                source_manager.get_source_values(
                    virtual_entity.id,
                ),
                write_state=False,
            )

            entities.append(sensor)
            sensor_manager.register_existing(sensor)

    async def _handle_state_changed(event: Event) -> None:
        """Handle Home Assistant state changes."""
        await handle_state_changed(
            source_manager,
            sensor_manager.sensors,
            event,
        )

    unsubscribe = hass.bus.async_listen(
        "state_changed",
        _handle_state_changed,
    )

    entry_data["sensor_unsubscribe"] = unsubscribe

    async_add_entities(entities)


def update_sensors_for_source_change(
    source_manager: SourceManager,
    sensors: Mapping[str, VirtualDeviceSensor],
    source_entity_id: str,
) -> None:
    """Update virtual sensors affected by a source change."""
    affected_entity_ids = source_manager.handle_source_change(
        source_entity_id,
    )

    for entity_id in affected_entity_ids:
        sensor = sensors.get(entity_id)

        if sensor is None:
            continue

        sensor.update_value(
            source_manager.get_source_values(
                entity_id,
            )
        )


async def handle_state_changed(
    source_manager: SourceManager,
    sensors: Mapping[str, VirtualDeviceSensor],
    event: Event,
) -> None:
    """Handle a Home Assistant state change."""
    new_state = event.data.get("new_state")

    if new_state is None:
        return

    source_entity_id = event.data["entity_id"]

    source_value = source_value_from_state(
        source_entity_id,
        new_state,
    )

    if source_value is None:
        return

    source_manager.update_source_value(
        source_value,
    )

    update_sensors_for_source_change(
        source_manager,
        sensors,
        source_entity_id,
    )


def source_value_from_state(
    entity_id: str,
    state: State,
) -> SourceValue | None:
    """Create a SourceValue from a Home Assistant state."""
    if state.state in (
        STATE_UNKNOWN,
        STATE_UNAVAILABLE,
    ):
        return None

    try:
        value = float(state.state)
    except (TypeError, ValueError):
        return None

    unit = state.attributes.get("unit_of_measurement")

    return SourceValue(
        entity_id=entity_id,
        value=value,
        unit=unit,
    )


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Unload Virtual Device Manager virtual sensors."""
    entry_data = hass.data[DOMAIN].pop(entry.entry_id, None)

    if entry_data is None:
        return True

    unsubscribe = entry_data.get("sensor_unsubscribe")

    if unsubscribe is not None:
        unsubscribe()

    return True
