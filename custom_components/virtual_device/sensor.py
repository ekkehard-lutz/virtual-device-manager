from collections.abc import Mapping

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import Event, HomeAssistant, State
from homeassistant.helpers.entity import DeviceInfo

from .aggregator import SourceValue, aggregate_values
from .const import DOMAIN
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

        self._attr_name = (
            entity.name if entity.name is not None else entity.device_class
        )

        self._attr_device_class = entity.device_class
        self._attr_native_unit_of_measurement = entity.unit
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
            self._virtual_entity.unit,
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
            name=self._device.name,
        )


class VirtualSensorManager:
    """Manage virtual sensors at runtime."""

    def __init__(self) -> None:
        """Initialize the sensor manager."""
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
        self._sensors[sensor._virtual_entity.id] = sensor

    def add_entity(
        self,
        device: VirtualDevice,
        entity: VirtualEntity,
        values: list[SourceValue],
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

    async def async_replace_entity(
        self,
        device: VirtualDevice,
        entity: VirtualEntity,
        values: list[SourceValue],
    ) -> None:
        """Replace a runtime sensor while retaining its registry unique ID."""
        await self.async_remove_entity(entity.id)
        self.add_entity(device, entity, values)


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
