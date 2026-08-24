"""Aggregation helpers for the Virtual Device Manager integration."""

from __future__ import annotations

from dataclasses import dataclass

from .device_class_metadata import get_device_class_metadata
from .unit_converter import convert_value


@dataclass(slots=True)
class SourceValue:
    """A numeric value from a source entity."""

    entity_id: str
    value: float
    unit: str


def aggregate_values(
    values: list[SourceValue],
    device_class: str,
    aggregation: str,
) -> float | None:
    """Aggregate source values in the native unit of the device class."""
    if not values:
        return None

    target_unit = get_device_class_metadata(device_class).native_unit

    converted_values = [
        convert_value(
            value.value,
            device_class,
            value.unit,
            target_unit,
        )
        for value in values
    ]

    if aggregation == "sum":
        return sum(converted_values)

    if aggregation == "avg":
        return sum(converted_values) / len(converted_values)

    if aggregation == "min":
        return min(converted_values)

    if aggregation == "max":
        return max(converted_values)

    raise ValueError(f"Unsupported aggregation: {aggregation}")
