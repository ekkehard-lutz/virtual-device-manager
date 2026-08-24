"""Unit conversion helpers for the Virtual Device Manager integration."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.sensor.const import UNIT_CONVERTERS
from homeassistant.const import UnitOfElectricCurrent, UnitOfElectricPotential
from homeassistant.exceptions import HomeAssistantError

KILOAMPERE = "kA"
KILOVOLT = "kV"


def convert_value(
    value: float,
    device_class: str,
    from_unit: str,
    to_unit: str,
) -> float:
    """Convert a value using Home Assistant's unit converter."""
    if from_unit == to_unit:
        return value

    # Home Assistant Core 2026.8 does not expose kA in UnitOfElectricCurrent.
    # Keep this narrow SI conversion in the shared layer so live and historical
    # aggregation still have identical semantics.
    if device_class == SensorDeviceClass.CURRENT:
        if from_unit == KILOAMPERE and to_unit == UnitOfElectricCurrent.AMPERE:
            return value * 1000
        if from_unit == UnitOfElectricCurrent.AMPERE and to_unit == KILOAMPERE:
            return value / 1000

    # kV is native to Home Assistant 2026.8. This fallback also keeps VDM's
    # development test runtime, which uses an older HA converter, compatible.
    if device_class == SensorDeviceClass.VOLTAGE:
        if from_unit == KILOVOLT and to_unit == UnitOfElectricPotential.VOLT:
            return value * 1000
        if from_unit == UnitOfElectricPotential.VOLT and to_unit == KILOVOLT:
            return value / 1000

    converter = UNIT_CONVERTERS.get(device_class)
    if converter is None:
        raise ValueError(
            f"No unit converter available for device class '{device_class}'."
        )

    try:
        return converter.convert(value, from_unit, to_unit)
    except (HomeAssistantError, ValueError, TypeError) as err:
        raise ValueError(
            f"Cannot convert '{from_unit}' to '{to_unit}' "
            f"for device class '{device_class}'."
        ) from err
