"""Tests for Home Assistant registry lifecycle management."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.virtual_device import lifecycle
from custom_components.virtual_device.const import DOMAIN
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
    device = VirtualDevice(id="virtual_light", label_ref="light")

    manager.async_ensure_device(device)

    device_registry.async_get_or_create.assert_called_once_with(
        config_entry_id="entry-1",
        identifiers=virtual_device_identifiers("virtual_light"),
        name=None,
    )


def test_ensure_device_stores_name_in_registry(monkeypatch) -> None:
    """Store the virtual device name in the Home Assistant device registry."""
    manager, _, device_registry, _ = _manager(monkeypatch)
    device = VirtualDevice(
        id="virtual_energy",
        label_ref="energy",
    )

    manager.async_ensure_device(
        device,
        name="Energie",
    )

    device_registry.async_get_or_create.assert_called_once_with(
        config_entry_id="entry-1",
        identifiers=virtual_device_identifiers("virtual_energy"),
        name="Energie",
    )


def test_ensure_device_updates_changed_name(monkeypatch) -> None:
    """Update the Home Assistant device name when it changes."""
    manager, _, device_registry, _ = _manager(monkeypatch)
    device = VirtualDevice(
        id="virtual_energy",
        label_ref="energy",
    )

    registry_entry = MagicMock()
    registry_entry.id = "device-registry-id"
    registry_entry.name = "Alte Energie"

    device_registry.async_get_or_create.return_value = registry_entry

    manager.async_ensure_device(
        device,
        name="Neue Energie",
    )

    device_registry.async_get_or_create.assert_called_once_with(
        config_entry_id="entry-1",
        identifiers=virtual_device_identifiers("virtual_energy"),
        name="Neue Energie",
    )

    device_registry.async_update_device.assert_called_once_with(
        "device-registry-id",
        name="Neue Energie",
    )


def test_ensuring_device_is_idempotent(monkeypatch) -> None:
    """Repeated setup uses the same stable device identifier."""
    manager, _, device_registry, _ = _manager(monkeypatch)
    device = VirtualDevice(id="virtual_light", label_ref="light")

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
            VirtualEntity("virtual_light_power", "power", "sum"),
            VirtualEntity("virtual_light_energy", "energy", "sum"),
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


def test_update_entity_name_updates_registry() -> None:
    """Update the Home Assistant entity registry name."""
    hass = MagicMock()
    sensor_manager = MagicMock()

    manager = VirtualDeviceLifecycleManager(
        hass,
        "entry-1",
        sensor_manager,
    )

    registry = MagicMock()
    registry.async_get_entity_id.return_value = "sensor.virtual_power"

    with patch(
        "custom_components.virtual_device.lifecycle.entity_registry.async_get",
        return_value=registry,
    ):
        manager.async_update_entity_name(
            "virtual_power",
            "Neue Hausleistung",
        )

    registry.async_update_entity.assert_called_once_with(
        "sensor.virtual_power",
        name="Neue Hausleistung",
    )


@pytest.mark.asyncio
async def test_remove_entity_removes_runtime_and_registry() -> None:
    """Remove a virtual entity from runtime and the entity registry."""
    hass = MagicMock()

    sensor_manager = MagicMock()
    sensor_manager.async_remove_entity = AsyncMock()

    manager = VirtualDeviceLifecycleManager(
        hass,
        "entry-1",
        sensor_manager,
    )

    registry = MagicMock()
    registry.async_get_entity_id.return_value = "sensor.virtual_power"

    with patch(
        "custom_components.virtual_device.lifecycle.entity_registry.async_get",
        return_value=registry,
    ):
        await manager.async_remove_entity("virtual_power")

    sensor_manager.async_remove_entity.assert_awaited_once_with(
        "virtual_power",
    )

    registry.async_get_entity_id.assert_called_once_with(
        "sensor",
        DOMAIN,
        "virtual_device_virtual_power",
    )

    registry.async_remove.assert_called_once_with(
        "sensor.virtual_power",
    )


@pytest.mark.asyncio
async def test_remove_device_removes_entities_and_device_registry_entry() -> None:
    """Remove all entities and the device registry entry."""
    hass = MagicMock()

    sensor_manager = MagicMock()
    sensor_manager.async_remove_entity = AsyncMock()
    sensor_manager.async_remove_entities_for_device = AsyncMock()

    manager = VirtualDeviceLifecycleManager(
        hass,
        "entry-1",
        sensor_manager,
    )

    device = VirtualDevice(
        id="device-1",
        label_ref="label-id",
        entities=[
            VirtualEntity(
                id="power",
                device_class="power",
                aggregation="sum",
            ),
            VirtualEntity(
                id="energy",
                device_class="energy",
                aggregation="sum",
            ),
        ],
    )

    entity_registry_mock = MagicMock()
    entity_registry_mock.async_get_entity_id.return_value = None

    device_registry_mock = MagicMock()
    device_registry_entry = MagicMock()
    device_registry_entry.id = "ha-device-1"
    device_registry_entry.config_entries = {"entry-1"}
    device_registry_mock.async_get_device_by_identifier.return_value = (
        device_registry_entry
    )

    with (
        patch(
            "custom_components.virtual_device.lifecycle.entity_registry.async_get",
            return_value=entity_registry_mock,
        ),
        patch(
            "custom_components.virtual_device.lifecycle.device_registry.async_get",
            return_value=device_registry_mock,
        ),
    ):
        await manager.async_remove_device(device)

    sensor_manager.async_remove_entities_for_device.assert_awaited_once_with(
        "device-1",
    )

    device_registry_mock.async_remove_device.assert_called_once_with(
        "ha-device-1",
    )
