"""Management operations for virtual devices."""

from homeassistant.core import HomeAssistant

from .models import (
    VirtualDevice,
)
from .source_manager import SourceManager
from .storage import VirtualDeviceStorage
from .virtual_device_workflow import (
    add_virtual_entity,
    create_virtual_device,
    delete_virtual_entity,
    update_virtual_device,
    update_virtual_entity,
)


async def async_create_virtual_device(
    hass: HomeAssistant,
    storage: VirtualDeviceStorage,
    label_ref: str,
    name: str | None,
) -> VirtualDevice:
    """Create and persist a virtual device."""
    device = create_virtual_device(
        hass=hass,
        label_ref=label_ref,
        name=name,
        existing_virtual_devices=storage.get_virtual_devices(),
    )

    await storage.async_save_virtual_device(device)

    return device


async def async_update_virtual_device(
    hass: HomeAssistant,
    storage: VirtualDeviceStorage,
    device_id: str,
    name: str | None = None,
    label_ref: str | None = None,
    confirm_physical_name_conflict: bool = False,
) -> VirtualDevice:
    """Update and persist an existing virtual device."""
    device = storage.get_virtual_device(device_id)

    if device is None:
        raise ValueError(
            f"Virtual device '{device_id}' does not exist"
        )

    updated_device = update_virtual_device(
        hass=hass,
        device=device,
        name=name,
        label_ref=label_ref,
        existing_virtual_devices=storage.get_virtual_devices(),
        confirm_physical_name_conflict=confirm_physical_name_conflict,
    )

    await storage.async_save_virtual_device(updated_device)

    return updated_device


async def async_add_virtual_entity(
    hass: HomeAssistant,
    storage: VirtualDeviceStorage,
    source_manager: SourceManager,
    device_id: str,
    device_class: str,
    aggregation: str,
    unit: str,
    name: str | None = None,
) -> VirtualDevice:
    """Add and persist a virtual entity."""
    device = storage.get_virtual_device(device_id)

    if device is None:
        raise ValueError(
            f"Virtual device '{device_id}' does not exist"
        )

    updated_device = add_virtual_entity(
        device=device,
        device_class=device_class,
        aggregation=aggregation,
        unit=unit,
        name=name,
    )

    await storage.async_save_virtual_device(
        updated_device
    )

    source_manager.rebuild_virtual_device(
        hass,
        updated_device,
    )

    return updated_device


async def async_update_virtual_entity(
    hass: HomeAssistant,
    storage: VirtualDeviceStorage,
    source_manager: SourceManager,
    device_id: str,
    entity_id: str,
    device_class: str | None = None,
    aggregation: str | None = None,
    unit: str | None = None,
    name: str | None = None,
) -> VirtualDevice:
    """Update and persist a virtual entity."""
    device = storage.get_virtual_device(device_id)

    if device is None:
        raise ValueError(
            f"Virtual device '{device_id}' does not exist"
        )

    updated_device = update_virtual_entity(
        device=device,
        entity_id=entity_id,
        device_class=device_class,
        aggregation=aggregation,
        unit=unit,
        name=name,
    )

    await storage.async_save_virtual_device(
        updated_device
    )

    source_manager.rebuild_virtual_device(
        hass,
        updated_device,
    )

    return updated_device


async def async_delete_virtual_entity(
    hass: HomeAssistant,
    storage: VirtualDeviceStorage,
    source_manager: SourceManager,
    device_id: str,
    entity_id: str,
) -> VirtualDevice:
    """Delete and persist a virtual entity."""
    device = storage.get_virtual_device(device_id)

    if device is None:
        raise ValueError(
            f"Virtual device '{device_id}' does not exist"
        )

    updated_device = delete_virtual_entity(
        device=device,
        entity_id=entity_id,
    )

    await storage.async_save_virtual_device(
        updated_device
    )

    source_manager.rebuild_virtual_device(
        hass,
        updated_device,
    )

    return updated_device


async def async_delete_virtual_device(
    hass: HomeAssistant,
    storage: VirtualDeviceStorage,
    device_id: str,
) -> None:
    """Delete a virtual device."""
    await storage.async_delete_virtual_device(device_id)

