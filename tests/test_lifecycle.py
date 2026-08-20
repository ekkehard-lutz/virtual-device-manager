"""Tests for Home Assistant registry lifecycle management."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.virtual_device import lifecycle
from custom_components.virtual_device.lifecycle import (
    VirtualDeviceLifecycleManager,
    virtual_device_identifiers,
    virtual_entity_unique_id,
)
from custom_components.virtual_device.models import VirtualDevice, VirtualEntity


def _entry(
    *,
    entity_id: str,
    unique_id: str,
    config_entry_id: str = "entry-1",
    platform: str = "virtual_device",
) -> SimpleNamespace:
    """Create a lightweight entity registry entry."""
    return SimpleNamespace(
        entity_id=entity_id,
        unique_id=unique_id,
        config_entry_id=config_entry_id,
        platform=platform,
    )


def _device_entry(
    *,
    device_id: str,
    identifier: str,
    config_entries: set[str] | None = None,
) -> SimpleNamespace:
    """Create a lightweight device registry entry."""
    return SimpleNamespace(
        id=device_id,
        identifiers={("virtual_device", identifier)},
        config_entries=config_entries or {"entry-1"},
    )


def _manager(monkeypatch):
    """Create a lifecycle manager with mocked Home Assistant registries."""
    hass = MagicMock()
    sensor_manager = MagicMock()
    sensor_manager.async_remove_entity = AsyncMock()
    sensor_manager.async_remove_entity_by_unique_id = AsyncMock()
    sensor_manager.async_remove_entities_for_device = AsyncMock()

    device_registry = MagicMock()
    device_registry.devices = {}
    device_registry.async_get_device_by_identifier.return_value = None

    entity_registry = MagicMock()
    entity_registry.entities = {}
    entity_registry.async_get_entity_id.return_value = None

    monkeypatch.setattr(
        lifecycle.device_registry,
        "async_get",
        lambda _: device_registry,
    )
    monkeypatch.setattr(
        lifecycle.entity_registry,
        "async_get",
        lambda _: entity_registry,
    )

    return (
        VirtualDeviceLifecycleManager(hass, "entry-1", sensor_manager),
        sensor_manager,
        device_registry,
        entity_registry,
    )


def test_empty_device_is_explicitly_registered(monkeypatch) -> None:
    """A device without entities is created in the device registry."""
    manager, _, device_registry, _ = _manager(monkeypatch)
    device = VirtualDevice(id="virtual_light", label_ref="light", name="Licht")

    manager.async_ensure_device(device)

    device_registry.async_get_or_create.assert_called_once_with(
        config_entry_id="entry-1",
        identifiers=virtual_device_identifiers("virtual_light"),
        name="Licht",
    )


def test_ensuring_device_is_idempotent(monkeypatch) -> None:
    """Repeated setup uses the same stable device identifier."""
    manager, _, device_registry, _ = _manager(monkeypatch)
    device = VirtualDevice(id="virtual_light", label_ref="light", name="Licht")

    manager.async_ensure_device(device)
    manager.async_ensure_device(device)

    assert device_registry.async_get_or_create.call_count == 2
    assert all(
        call.kwargs["identifiers"] == virtual_device_identifiers("virtual_light")
        for call in device_registry.async_get_or_create.call_args_list
    )


@pytest.mark.asyncio
async def test_delete_entity_removes_runtime_and_registry(monkeypatch) -> None:
    """Deleting an entity removes its active object and registry entry."""
    manager, sensor_manager, _, entity_registry = _manager(monkeypatch)
    entity_registry.async_get_entity_id.return_value = "sensor.light_power"

    await manager.async_remove_entity("virtual_light_power")

    sensor_manager.async_remove_entity.assert_awaited_once_with("virtual_light_power")
    entity_registry.async_remove.assert_called_once_with("sensor.light_power")


@pytest.mark.asyncio
async def test_delete_device_removes_all_entities_and_registry(monkeypatch) -> None:
    """Deleting a device first removes each of its entities."""
    manager, sensor_manager, device_registry, entity_registry = _manager(monkeypatch)
    device_registry.async_get_device_by_identifier.return_value = _device_entry(
        device_id="registry-device",
        identifier="virtual_light",
    )
    device = VirtualDevice(
        id="virtual_light",
        label_ref="light",
        entities=[
            VirtualEntity("virtual_light_power", "power", "sum", "W"),
            VirtualEntity("virtual_light_energy", "energy", "sum", "kWh"),
        ],
    )

    await manager.async_remove_device(device)

    assert sensor_manager.async_remove_entity.await_count == 2
    sensor_manager.async_remove_entities_for_device.assert_awaited_once_with(
        "virtual_light"
    )
    device_registry.async_remove_device.assert_called_once_with("registry-device")
    assert entity_registry.async_remove.call_count == 0


@pytest.mark.asyncio
async def test_reconcile_removes_only_orphaned_vdm_entries(monkeypatch) -> None:
    """Reconciliation leaves foreign registry entries untouched."""
    manager, sensor_manager, device_registry, entity_registry = _manager(monkeypatch)
    orphan_entity = _entry(
        entity_id="sensor.orphan",
        unique_id=virtual_entity_unique_id("virtual_old_power"),
    )
    foreign_entity = _entry(
        entity_id="sensor.foreign",
        unique_id=virtual_entity_unique_id("virtual_foreign_power"),
        config_entry_id="foreign-entry",
    )
    entity_registry.entities = {
        orphan_entity.entity_id: orphan_entity,
        foreign_entity.entity_id: foreign_entity,
    }
    orphan_device = _device_entry(
        device_id="orphan-device",
        identifier="virtual_old",
    )
    foreign_device = _device_entry(
        device_id="foreign-device",
        identifier="virtual_foreign",
        config_entries={"foreign-entry"},
    )
    device_registry.devices = {
        orphan_device.id: orphan_device,
        foreign_device.id: foreign_device,
    }
    device_registry.async_get_device.return_value = orphan_device

    await manager.async_reconcile([])

    entity_registry.async_remove.assert_called_once_with("sensor.orphan")
    sensor_manager.async_remove_entity_by_unique_id.assert_awaited_once_with(
        orphan_entity.unique_id
    )
    device_registry.async_remove_device.assert_called_once_with("orphan-device")
