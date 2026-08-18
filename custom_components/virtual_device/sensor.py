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

        self._attr_unique_id = (
            f"virtual_device_{entity.id}"
        )

        self._attr_name = (
            entity.name
            if entity.name is not None
            else entity.device_class
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


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Set up Virtual Device Manager virtual sensors."""
    entry_data = hass.data[DOMAIN][entry.entry_id]
    storage = entry_data["storage"]

    source_manager = entry_data["source_manager"]

    entities: list[VirtualDeviceSensor] = []
    sensors: dict[str, VirtualDeviceSensor] = {}

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
            sensors[virtual_entity.id] = sensor

    async def _handle_state_changed(event: Event) -> None:
        """Handle Home Assistant state changes."""
        await handle_state_changed(
            source_manager,
            sensors,
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

    unit = state.attributes.get(
        "unit_of_measurement"
    )

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
