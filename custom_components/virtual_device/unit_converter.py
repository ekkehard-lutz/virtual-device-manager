"""Unit conversion helpers for the Virtual Device Manager integration."""

from __future__ import annotations

from homeassistant.components.sensor.const import (
    DEVICE_CLASS_UNITS,
)

from .validation import can_convert_unit


def _get_prefix_factor(unit: str) -> tuple[str, float]:
    """Return base unit and SI prefix factor."""
    prefixes = (
        ("G", 1_000_000_000.0),
        ("M", 1_000_000.0),
        ("k", 1_000.0),
        ("m", 0.001),
    )

    for prefix, factor in prefixes:
        if unit.startswith(prefix) and len(unit) > len(prefix):
            return unit[len(prefix):], factor

    return unit, 1.0


def convert_value(
    value: float,
    device_class: str,
    from_unit: str,
    to_unit: str,
) -> float:
    """Convert a value between compatible SI-prefixed units."""
    if from_unit == to_unit:
        if from_unit not in DEVICE_CLASS_UNITS.get(device_class, ()):
            raise ValueError(
                f"Unit '{from_unit}' is not valid for "
                f"device class '{device_class}'."
            )
        return value

    if not can_convert_unit(device_class, from_unit, to_unit):
        raise ValueError(
            f"Cannot convert '{from_unit}' to '{to_unit}' "
            f"for device class '{device_class}'."
        )

    from_base, from_factor = _get_prefix_factor(from_unit)
    to_base, to_factor = _get_prefix_factor(to_unit)

    if from_base != to_base:
        raise ValueError(
            f"Units '{from_unit}' and '{to_unit}' "
            "do not use the same base unit."
        )

    return value * from_factor / to_factor
