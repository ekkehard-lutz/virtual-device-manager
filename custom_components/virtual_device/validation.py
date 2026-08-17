"""Validation helpers for the Virtual Device Manager integration."""

from homeassistant.components.sensor.const import (
    DEVICE_CLASS_UNITS,
    UNIT_CONVERTERS,
)
from .const import AGGREGATIONS

class ValidationError(ValueError):
    """Raised when Virtual Device Manager configuration is invalid."""

from .models import VirtualDevice, VirtualEntity


def validate_virtual_entity(entity: VirtualEntity) -> None:
    """Validate a virtual entity configuration."""
    if not entity.device_class:
        raise ValidationError("Device class must not be empty.")

    if not is_valid_aggregation(entity.aggregation):
        raise ValidationError(
            f"Unsupported aggregation: {entity.aggregation}"
        )

    if not entity.unit:
        raise ValidationError("Unit must not be empty.")

    if not is_valid_unit_for_device_class(
        entity.device_class,
        entity.unit,
    ):
        raise ValidationError(
            f"Unit '{entity.unit}' is not valid for "
            f"device class '{entity.device_class}'."
        )
    

def is_valid_unit_for_device_class(
    device_class: str,
    unit: str,
) -> bool:
    """Return whether a unit is valid for a device class."""
    units = DEVICE_CLASS_UNITS.get(device_class)

    if units is None:
        return False

    return unit in units


def can_convert_unit(
    device_class: str,
    from_unit: str,
    to_unit: str,
) -> bool:
    """Return whether two units can be converted for a device class."""
    if from_unit == to_unit:
        return is_valid_unit_for_device_class(device_class, from_unit)

    converter = UNIT_CONVERTERS.get(device_class)

    if converter is None:
        return False

    return (
        from_unit in converter.VALID_UNITS
        and to_unit in converter.VALID_UNITS
    )


def is_valid_aggregation(aggregation: str) -> bool:
    """Return whether an aggregation method is supported."""
    return aggregation in AGGREGATIONS


def validate_virtual_device(device: VirtualDevice) -> None:
    """Validate a virtual device configuration."""
    if not device.label_ref:
        raise ValidationError("Label must not be empty.")

    entity_ids: set[str] = set()

    for entity in device.entities:
        if entity.id in entity_ids:
            raise ValidationError(
                f"Duplicate virtual entity ID: {entity.id}"
            )

        entity_ids.add(entity.id)

        validate_virtual_entity(entity)
