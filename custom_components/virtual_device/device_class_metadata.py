"""Central device-class metadata for Virtual Device Manager entities."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfEnergy, UnitOfPower


@dataclass(frozen=True, slots=True)
class DeviceClassMetadata:
    """Home Assistant metadata shared by live and historical VDM code."""

    native_unit: str
    state_class: SensorStateClass


DEVICE_CLASS_METADATA: dict[str, DeviceClassMetadata] = {
    SensorDeviceClass.ENERGY: DeviceClassMetadata(
        native_unit=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorDeviceClass.POWER: DeviceClassMetadata(
        native_unit=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
}


def get_device_class_metadata(device_class: str) -> DeviceClassMetadata:
    """Return metadata for a supported device class."""
    try:
        return DEVICE_CLASS_METADATA[device_class]
    except KeyError as err:
        raise ValueError(f"Unsupported device class: {device_class}") from err
