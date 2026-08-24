"""Workflow helpers for virtual devices."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers import label_registry

from .models import VirtualDevice, VirtualEntity
from .validation import validate_virtual_entity


class VirtualDeviceLabelConflict(Exception):
    """Raised when a label is already assigned to a virtual device."""


def generate_virtual_entity_id(
    device_id: str,
    device_class: str,
    existing_entities: list[VirtualEntity],
) -> str:
    """Generate a unique ID for a virtual entity."""
    base_id = f"{device_id}_{device_class}"

    existing_ids = {entity.id for entity in existing_entities}

    if base_id not in existing_ids:
        return base_id

    index = 1

    while f"{base_id}_{index}" in existing_ids:
        index += 1

    return f"{base_id}_{index}"


def create_virtual_entity(
    device: VirtualDevice,
    device_class: str,
    aggregation: str,
) -> VirtualEntity:
    """Create a new virtual entity."""
    entity_id = generate_virtual_entity_id(
        device.id,
        device_class,
        device.entities,
    )

    entity = VirtualEntity(
        id=entity_id,
        device_class=device_class,
        aggregation=aggregation,
    )

    validate_virtual_entity(entity)

    return entity


def add_virtual_entity(
    device: VirtualDevice,
    device_class: str,
    aggregation: str,
) -> VirtualDevice:
    """Add a new virtual entity to a virtual device."""
    entity = create_virtual_entity(
        device=device,
        device_class=device_class,
        aggregation=aggregation,
    )

    return VirtualDevice(
        id=device.id,
        label_ref=device.label_ref,
        entities=[
            *device.entities,
            entity,
        ],
    )


def update_virtual_entity(
    device: VirtualDevice,
    entity_id: str,
    *,
    device_class: str | None = None,
    aggregation: str | None = None,
) -> VirtualDevice:
    """Update an existing virtual entity."""
    existing_entity = next(
        (entity for entity in device.entities if entity.id == entity_id),
        None,
    )

    if existing_entity is None:
        raise ValueError(f"Virtual entity '{entity_id}' does not exist")

    new_aggregation = (
        aggregation if aggregation is not None else existing_entity.aggregation
    )
    new_device_class = (
        device_class if device_class is not None else existing_entity.device_class
    )

    updated_entity = VirtualEntity(
        id=existing_entity.id,
        device_class=new_device_class,
        aggregation=new_aggregation,
    )

    validate_virtual_entity(updated_entity)

    updated_entities = [
        updated_entity if entity.id == entity_id else entity
        for entity in device.entities
    ]

    return VirtualDevice(
        id=device.id,
        label_ref=device.label_ref,
        entities=updated_entities,
    )


def delete_virtual_entity(
    device: VirtualDevice,
    entity_id: str,
) -> VirtualDevice:
    """Delete an existing virtual entity."""
    if not any(entity.id == entity_id for entity in device.entities):
        raise ValueError(f"Virtual entity '{entity_id}' does not exist")

    remaining_entities = [
        entity for entity in device.entities if entity.id != entity_id
    ]

    return VirtualDevice(
        id=device.id,
        label_ref=device.label_ref,
        entities=remaining_entities,
    )


def create_virtual_device(
    hass: HomeAssistant,
    label_ref: str,
    existing_virtual_devices: list[VirtualDevice],
) -> VirtualDevice:
    """Create a virtual device from a Home Assistant label."""
    registry = label_registry.async_get(hass)

    label_entry = registry.async_get_label(label_ref)

    if label_entry is None:
        raise ValueError(f"Label '{label_ref}' does not exist")

    # A label can only be assigned to one virtual device.
    if any(device.label_ref == label_ref for device in existing_virtual_devices):
        raise VirtualDeviceLabelConflict(
            f"Label '{label_ref}' is already assigned to a virtual device"
        )

    return VirtualDevice(
        id=f"virtual_{label_ref}",
        label_ref=label_ref,
    )


def update_virtual_device(
    hass: HomeAssistant,
    device: VirtualDevice,
    existing_virtual_devices: list[VirtualDevice],
    *,
    label_ref: str | None = None,
    confirm_physical_name_conflict: bool = False,
) -> VirtualDevice:
    """Update an existing virtual device."""
    if label_ref is not None and label_ref != device.label_ref:
        raise ValueError("Label cannot be changed")

    registry = label_registry.async_get(hass)

    label_entry = registry.async_get_label(device.label_ref)

    if label_entry is None:
        raise ValueError(f"Label '{device.label_ref}' does not exist")

    return VirtualDevice(
        id=device.id,
        label_ref=device.label_ref,
        entities=device.entities.copy(),
    )
