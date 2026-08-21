"""Workflow helpers for virtual devices."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry, label_registry

from .const import DOMAIN
from .models import VirtualDevice, VirtualEntity
from .validation import validate_virtual_entity


class VirtualDeviceNameConflict(Exception):
    """Raised when a virtual device name is already in use."""


class VirtualDeviceLabelConflict(Exception):
    """Raised when a label is already assigned to a virtual device."""


class PhysicalDeviceNameConflict(Exception):
    """Raised when a physical device already uses the requested name."""


def has_physical_device_name_conflict(
    hass: HomeAssistant,
    name: str,
) -> bool:
    """Return whether a physical device already uses this name."""
    registry = device_registry.async_get(hass)

    return any(
        device.name == name
        and not any(
            identifier_domain == DOMAIN for identifier_domain, _ in device.identifiers
        )
        for device in registry.devices.values()
    )


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
    name: str | None = None,
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
        name=name,
    )

    validate_virtual_entity(entity)

    return entity


def add_virtual_entity(
    device: VirtualDevice,
    device_class: str,
    aggregation: str,
    name: str | None = None,
) -> VirtualDevice:
    """Add a new virtual entity to a virtual device."""
    entity = create_virtual_entity(
        device=device,
        device_class=device_class,
        aggregation=aggregation,
        name=name,
    )

    return VirtualDevice(
        id=device.id,
        label_ref=device.label_ref,
        name=device.name,
        entities=[
            *device.entities,
            entity,
        ],
    )


def update_virtual_entity(
    device: VirtualDevice,
    entity_id: str,
    *,
    aggregation: str | None = None,
    name: str | None = None,
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

    new_name = name if name is not None else existing_entity.name

    updated_entity = VirtualEntity(
        id=existing_entity.id,
        device_class=existing_entity.device_class,
        aggregation=new_aggregation,
        name=new_name,
    )

    validate_virtual_entity(updated_entity)

    updated_entities = [
        updated_entity if entity.id == entity_id else entity
        for entity in device.entities
    ]

    return VirtualDevice(
        id=device.id,
        label_ref=device.label_ref,
        name=device.name,
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
        name=device.name,
        entities=remaining_entities,
    )


def create_virtual_device(
    hass: HomeAssistant,
    label_ref: str,
    name: str | None,
    existing_virtual_devices: list[VirtualDevice],
    confirm_physical_name_conflict: bool = False,
) -> VirtualDevice:
    """Create a virtual device from a Home Assistant label."""
    registry = label_registry.async_get(hass)

    label_entry = registry.async_get_label(label_ref)

    if label_entry is None:
        raise ValueError(f"Label '{label_ref}' does not exist")

    device_name = name or label_entry.name

    # A label can only be assigned to one virtual device.
    if any(device.label_ref == label_ref for device in existing_virtual_devices):
        raise VirtualDeviceLabelConflict(
            f"Label '{label_ref}' is already assigned to a virtual device"
        )

    # A virtual device must never have the same name as another
    # virtual device.
    if any(device.name == device_name for device in existing_virtual_devices):
        raise VirtualDeviceNameConflict(
            f"Virtual device '{device_name}' already exists"
        )

    # A physical device with the same name requires explicit confirmation.
    if (
        has_physical_device_name_conflict(hass, device_name)
        and not confirm_physical_name_conflict
    ):
        raise PhysicalDeviceNameConflict(
            f"Physical device '{device_name}' already exists"
        )

    return VirtualDevice(
        id=f"virtual_{label_ref}",
        label_ref=label_ref,
        name=device_name,
    )


def update_virtual_device(
    hass: HomeAssistant,
    device: VirtualDevice,
    existing_virtual_devices: list[VirtualDevice],
    *,
    label_ref: str | None = None,
    name: str | None = None,
    confirm_physical_name_conflict: bool = False,
) -> VirtualDevice:
    """Update an existing virtual device."""
    registry = label_registry.async_get(hass)

    new_label_ref = label_ref if label_ref is not None else device.label_ref

    label_entry = registry.async_get_label(new_label_ref)

    if label_entry is None:
        raise ValueError(f"Label '{new_label_ref}' does not exist")

    new_name = name if name is not None else device.name

    # A label can only be assigned to one virtual device.
    # The current device itself is allowed to keep its label.
    if any(
        other.id != device.id and other.label_ref == new_label_ref
        for other in existing_virtual_devices
    ):
        raise VirtualDeviceLabelConflict(
            f"Label '{new_label_ref}' is already assigned to another virtual device"
        )

    # A virtual device must never have the same name
    # as another virtual device.
    # The current device itself is allowed to keep its name.
    if any(
        other.id != device.id and other.name == new_name
        for other in existing_virtual_devices
    ):
        raise VirtualDeviceNameConflict(f"Virtual device '{new_name}' already exists")

    # A physical device with the same name requires
    # explicit confirmation.
    if (
        has_physical_device_name_conflict(
            hass,
            new_name,
        )
        and not confirm_physical_name_conflict
    ):
        raise PhysicalDeviceNameConflict(f"Physical device '{new_name}' already exists")

    return VirtualDevice(
        id=device.id,
        label_ref=new_label_ref,
        name=new_name,
        entities=device.entities.copy(),
    )
