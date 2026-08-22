"""Unit conversion helpers for the Virtual Device Manager integration."""

from __future__ import annotations

from homeassistant.components.sensor.const import UNIT_CONVERTERS
from homeassistant.exceptions import HomeAssistantError


def convert_value(
    value: float,
    device_class: str,
    from_unit: str,
    to_unit: str,
) -> float:
    """Convert a value using Home Assistant's unit converter."""
    if from_unit == to_unit:
        return value

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
