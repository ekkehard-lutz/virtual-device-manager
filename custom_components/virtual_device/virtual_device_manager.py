"""Management operations for virtual devices."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers import label_registry

from .lifecycle import VirtualDeviceLifecycleManager
from .models import VirtualDevice
from .sensor import VirtualSensorManager
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
    lifecycle_manager: VirtualDeviceLifecycleManager | None = None,
) -> VirtualDevice:
    """Create and persist a virtual device."""
    device = create_virtual_device(
        hass=hass,
        label_ref=label_ref,
        existing_virtual_devices=storage.get_virtual_devices(),
    )

    if name is None:
        label_entry = label_registry.async_get(hass).async_get_label(label_ref)
        name = label_entry.name if label_entry is not None else None

    await storage.async_save_virtual_device(device)
    if lifecycle_manager is not None:
        lifecycle_manager.async_ensure_device(
            device,
            name=name,
        )

    return device


async def async_update_virtual_device(
    hass: HomeAssistant,
    storage: VirtualDeviceStorage,
    device_id: str,
    name: str | None = None,
    label_ref: str | None = None,
    confirm_physical_name_conflict: bool = False,
    lifecycle_manager: VirtualDeviceLifecycleManager | None = None,
) -> VirtualDevice:
    """Update and persist an existing virtual device."""
    device = storage.get_virtual_device(device_id)

    if device is None:
        raise ValueError(f"Virtual device '{device_id}' does not exist")

    updated_device = update_virtual_device(
        hass=hass,
        device=device,
        label_ref=label_ref,
        existing_virtual_devices=storage.get_virtual_devices(),
        confirm_physical_name_conflict=confirm_physical_name_conflict,
    )

    await storage.async_save_virtual_device(updated_device)
    if lifecycle_manager is not None:
        lifecycle_manager.async_ensure_device(
            updated_device,
            name=name,
        )

    return updated_device


async def async_add_virtual_entity(
    hass: HomeAssistant,
    storage: VirtualDeviceStorage,
    source_manager: SourceManager,
    sensor_manager: VirtualSensorManager,
    device_id: str,
    device_class: str,
    aggregation: str,
    name: str | None = None,
    lifecycle_manager: VirtualDeviceLifecycleManager | None = None,
) -> VirtualDevice:
    """Add and persist a virtual entity."""
    device = storage.get_virtual_device(device_id)

    if device is None:
        raise ValueError(f"Virtual device '{device_id}' does not exist")

    updated_device = add_virtual_entity(
        device=device,
        device_class=device_class,
        aggregation=aggregation,
    )

    await storage.async_save_virtual_device(updated_device)

    source_manager.rebuild_virtual_device(
        hass,
        updated_device,
    )

    virtual_entity = next(
        entity
        for entity in updated_device.entities
        if entity.id not in sensor_manager.sensors
    )

    registry_device_id = (
        lifecycle_manager.get_device_registry_id(updated_device.id)
        if lifecycle_manager is not None
        else None
    )

    sensor_manager.add_entity(
        device=updated_device,
        entity=virtual_entity,
        values=source_manager.get_source_values(
            virtual_entity.id,
        ),
        name=name,
        device_id=registry_device_id,
    )

    if lifecycle_manager is not None:
        lifecycle_manager.async_reconcile_device_entities(updated_device)

    return updated_device


async def async_update_virtual_entity(
    hass: HomeAssistant,
    storage: VirtualDeviceStorage,
    source_manager: SourceManager,
    device_id: str,
    entity_id: str,
    aggregation: str | None = None,
    name: str | None = None,
    sensor_manager: VirtualSensorManager | None = None,
    lifecycle_manager: VirtualDeviceLifecycleManager | None = None,
) -> VirtualDevice:
    """Update and persist a virtual entity."""
    device = storage.get_virtual_device(device_id)

    if device is None:
        raise ValueError(f"Virtual device '{device_id}' does not exist")

    updated_device = update_virtual_entity(
        device=device,
        entity_id=entity_id,
        aggregation=aggregation,
    )

    await storage.async_save_virtual_device(updated_device)

    if lifecycle_manager is not None:
        lifecycle_manager.async_update_entity_name(
            entity_id,
            name=name,
        )

    source_manager.rebuild_virtual_device(
        hass,
        updated_device,
    )

    updated_entity = next(
        entity for entity in updated_device.entities if entity.id == entity_id
    )

    if sensor_manager is not None:
        await sensor_manager.async_replace_entity(
            device=updated_device,
            entity=updated_entity,
            values=source_manager.get_source_values(entity_id),
            name=name,
        )

    return updated_device


async def async_delete_virtual_entity(
    hass: HomeAssistant,
    storage: VirtualDeviceStorage,
    source_manager: SourceManager,
    device_id: str,
    entity_id: str,
    lifecycle_manager: VirtualDeviceLifecycleManager | None = None,
) -> VirtualDevice:
    """Delete and persist a virtual entity."""
    device = storage.get_virtual_device(device_id)

    if device is None:
        raise ValueError(f"Virtual device '{device_id}' does not exist")

    if lifecycle_manager is not None:
        await lifecycle_manager.async_remove_entity(entity_id)
    source_manager.remove_virtual_entity(entity_id)

    if not any(entity.id == entity_id for entity in device.entities):
        return device

    updated_device = delete_virtual_entity(
        device=device,
        entity_id=entity_id,
    )

    await storage.async_save_virtual_device(updated_device)

    source_manager.rebuild_virtual_device(
        hass,
        updated_device,
    )

    return updated_device


async def async_delete_virtual_device(
    hass: HomeAssistant,
    storage: VirtualDeviceStorage,
    device_id: str,
    source_manager: SourceManager | None = None,
    lifecycle_manager: VirtualDeviceLifecycleManager | None = None,
) -> None:
    """Delete a virtual device."""
    device = storage.get_virtual_device(device_id)

    if device is None:
        if lifecycle_manager is not None:
            await lifecycle_manager.async_remove_device_entities(
                VirtualDevice(id=device_id, label_ref="")
            )

        if source_manager is not None:
            source_manager.remove_virtual_device(device_id)

        if lifecycle_manager is not None:
            lifecycle_manager.async_remove_device_registry_entry(device_id)

        await storage.async_delete_virtual_device(device_id)
        return

    if lifecycle_manager is not None:
        await lifecycle_manager.async_remove_device_entities(device)

    if source_manager is not None:
        source_manager.remove_virtual_device(device_id)

    if lifecycle_manager is not None:
        lifecycle_manager.async_remove_device_registry_entry(device_id)

    await storage.async_delete_virtual_device(device_id)
