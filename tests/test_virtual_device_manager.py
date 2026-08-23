"""Tests for the virtual device manager."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.virtual_device.models import (
    VirtualDevice,
    VirtualEntity,
)
from custom_components.virtual_device.virtual_device_manager import (
    async_add_virtual_entity,
    async_create_virtual_device,
    async_delete_virtual_device,
    async_delete_virtual_entity,
    async_update_virtual_device,
    async_update_virtual_entity,
)


@pytest.mark.asyncio
async def test_create_virtual_device_saves_device() -> None:
    """Create a virtual device and persist it."""
    hass = MagicMock()

    storage = MagicMock()
    storage.get_virtual_devices.return_value = []
    storage.async_save_virtual_device = AsyncMock()

    device = VirtualDevice(
        id="device-1",
        label_ref="label-id-energie",
    )

    with patch(
        "custom_components.virtual_device.virtual_device_manager.create_virtual_device",
        return_value=device,
    ) as create_mock:
        result = await async_create_virtual_device(
            hass=hass,
            storage=storage,
            label_ref="label-id-energie",
            name="Haus Energie",
        )

    assert result is device
    create_mock.assert_called_once()
    storage.async_save_virtual_device.assert_awaited_once_with(device)


@pytest.mark.asyncio
async def test_create_virtual_device_uses_label_name_as_registry_default() -> None:
    """Write the label display name only to the HA device registry."""
    hass = MagicMock()
    storage = MagicMock()
    storage.get_virtual_devices.return_value = []
    storage.async_save_virtual_device = AsyncMock()
    lifecycle_manager = MagicMock()
    device = VirtualDevice(id="virtual_abrakadabra", label_ref="abrakadabra")
    labels = MagicMock()
    label_entry = MagicMock()
    label_entry.name = "Abrakadabra"
    labels.async_get_label.return_value = label_entry

    with (
        patch(
            "custom_components.virtual_device.virtual_device_manager."
            "create_virtual_device",
            return_value=device,
        ),
        patch(
            "custom_components.virtual_device.virtual_device_manager."
            "label_registry.async_get",
            return_value=labels,
        ),
    ):
        result = await async_create_virtual_device(
            hass=hass,
            storage=storage,
            label_ref="abrakadabra",
            name=None,
            lifecycle_manager=lifecycle_manager,
        )

    assert result is device
    assert not hasattr(device, "name")
    lifecycle_manager.async_ensure_device.assert_called_once_with(
        device, name="Abrakadabra"
    )


@pytest.mark.asyncio
async def test_create_virtual_device_explicit_registry_name_wins() -> None:
    """Prefer an explicit device name without consulting the label registry."""
    hass = MagicMock()
    storage = MagicMock()
    storage.get_virtual_devices.return_value = []
    storage.async_save_virtual_device = AsyncMock()
    lifecycle_manager = MagicMock()
    device = VirtualDevice(id="virtual_abrakadabra", label_ref="abrakadabra")

    with patch(
        "custom_components.virtual_device.virtual_device_manager."
        "create_virtual_device",
        return_value=device,
    ):
        await async_create_virtual_device(
            hass=hass,
            storage=storage,
            label_ref="abrakadabra",
            name="Zaubergerät",
            lifecycle_manager=lifecycle_manager,
        )

    lifecycle_manager.async_ensure_device.assert_called_once_with(
        device, name="Zaubergerät"
    )


@pytest.mark.asyncio
async def test_update_virtual_device_saves_updated_device() -> None:
    """Update a virtual device and persist the result."""
    hass = MagicMock()

    existing = VirtualDevice(
        id="device-1",
        label_ref="label-id-energie",
    )

    updated = VirtualDevice(
        id="device-1",
        label_ref="label-id-energie",
    )

    storage = MagicMock()
    storage.get_virtual_device.return_value = existing
    storage.get_virtual_devices.return_value = [existing]
    storage.async_save_virtual_device = AsyncMock()

    with patch(
        "custom_components.virtual_device.virtual_device_manager.update_virtual_device",
        return_value=updated,
    ) as update_mock:
        result = await async_update_virtual_device(
            hass=hass,
            storage=storage,
            device_id="device-1",
            name="Haus Gesamtenergie",
        )

    assert result is updated
    update_mock.assert_called_once()
    storage.async_save_virtual_device.assert_awaited_once_with(updated)


@pytest.mark.asyncio
async def test_update_virtual_device_with_label_ref_updates_label() -> None:
    """Updating with a label reference changes the device label."""
    hass = MagicMock()
    storage = MagicMock()

    existing = VirtualDevice(
        id="device-1",
        label_ref="label-id-energie",
    )

    updated = VirtualDevice(
        id="device-1",
        label_ref="label-id-gesamt",
    )

    storage.get_virtual_device.return_value = existing
    storage.get_virtual_devices.return_value = [existing]
    storage.async_save_virtual_device = AsyncMock()

    with patch(
        "custom_components.virtual_device.virtual_device_manager.update_virtual_device",
        return_value=updated,
    ) as update_mock:
        result = await async_update_virtual_device(
            hass=hass,
            storage=storage,
            device_id="device-1",
            label_ref="label-id-gesamt",
        )

    assert result is updated

    update_mock.assert_called_once()
    storage.async_save_virtual_device.assert_awaited_once_with(updated)


@pytest.mark.asyncio
async def test_delete_virtual_device_removes_device() -> None:
    """Delete a virtual device from storage."""
    hass = MagicMock()

    storage = MagicMock()
    storage.async_delete_virtual_device = AsyncMock()

    await async_delete_virtual_device(
        hass=hass,
        storage=storage,
        device_id="device-1",
    )

    storage.async_delete_virtual_device.assert_awaited_once_with("device-1")


@pytest.mark.asyncio
async def test_delete_virtual_device_runs_full_lifecycle_before_storage() -> None:
    """Delete runtime entities, sources, and registry before stored config."""
    hass = MagicMock()
    device = VirtualDevice(
        id="device-1",
        label_ref="label-1",
        entities=[
            VirtualEntity("device-1_power", "power", "sum"),
            VirtualEntity("device-1_energy", "energy", "sum"),
        ],
    )
    storage = MagicMock()
    storage.get_virtual_device.return_value = device
    storage.async_delete_virtual_device = AsyncMock()
    source_manager = MagicMock()
    lifecycle_manager = MagicMock()
    lifecycle_manager.async_remove_device_entities = AsyncMock()

    await async_delete_virtual_device(
        hass=hass,
        storage=storage,
        device_id="device-1",
        source_manager=source_manager,
        lifecycle_manager=lifecycle_manager,
    )

    lifecycle_manager.async_remove_device_entities.assert_awaited_once_with(device)
    source_manager.remove_virtual_device.assert_called_once_with("device-1")
    lifecycle_manager.async_remove_device_registry_entry.assert_called_once_with(
        "device-1"
    )
    storage.async_delete_virtual_device.assert_awaited_once_with("device-1")


@pytest.mark.asyncio
async def test_repeated_entity_delete_is_idempotent() -> None:
    """Deleting an already removed entity keeps the remaining device intact."""
    hass = MagicMock()
    device = VirtualDevice(id="device-1", label_ref="label-1")
    storage = MagicMock()
    storage.get_virtual_device.return_value = device
    storage.async_save_virtual_device = AsyncMock()
    source_manager = MagicMock()
    lifecycle_manager = MagicMock()
    lifecycle_manager.async_remove_entity = AsyncMock()

    result = await async_delete_virtual_entity(
        hass=hass,
        storage=storage,
        source_manager=source_manager,
        device_id="device-1",
        entity_id="device-1_power",
        lifecycle_manager=lifecycle_manager,
    )

    assert result is device
    lifecycle_manager.async_remove_entity.assert_awaited_once_with("device-1_power")
    source_manager.remove_virtual_entity.assert_called_once_with("device-1_power")
    storage.async_save_virtual_device.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_virtual_device_rejects_unknown_device() -> None:
    """Reject an update for a device that does not exist."""
    hass = MagicMock()

    storage = MagicMock()
    storage.get_virtual_device.return_value = None

    with pytest.raises(ValueError, match="does not exist"):
        await async_update_virtual_device(
            hass=hass,
            storage=storage,
            device_id="unknown-device",
            name="Neuer Name",
        )


@pytest.mark.asyncio
async def test_add_virtual_entity_saves_updated_device() -> None:
    """Add a virtual entity and persist the result."""
    hass = MagicMock()

    existing = VirtualDevice(
        id="virtual_beleuchtung",
        label_ref="beleuchtung",
    )

    updated = VirtualDevice(
        id="virtual_beleuchtung",
        label_ref="beleuchtung",
        entities=[
            VirtualEntity(
                id="virtual_beleuchtung_power",
                device_class="power",
                aggregation="sum",
            ),
        ],
    )

    storage = MagicMock()
    storage.get_virtual_device.return_value = existing
    storage.async_save_virtual_device = AsyncMock()

    source_manager = MagicMock()
    sensor_manager = MagicMock()

    with patch(
        "custom_components.virtual_device.virtual_device_manager.add_virtual_entity",
        return_value=updated,
    ) as add_mock:
        result = await async_add_virtual_entity(
            hass=hass,
            storage=storage,
            source_manager=source_manager,
            sensor_manager=sensor_manager,
            device_id="virtual_beleuchtung",
            device_class="power",
            aggregation="sum",
        )

    source_manager.rebuild_virtual_device.assert_called_once_with(
        hass,
        updated,
    )

    assert result is updated
    add_mock.assert_called_once_with(
        device=existing,
        device_class="power",
        aggregation="sum",
    )
    storage.async_save_virtual_device.assert_awaited_once_with(updated)


@pytest.mark.asyncio
async def test_runtime_entity_is_immediately_assigned_to_device() -> None:
    """Assign a newly created runtime entity to its HA device immediately."""
    hass = MagicMock()
    existing = VirtualDevice(
        id="virtual_beleuchtung",
        label_ref="beleuchtung",
    )
    storage = MagicMock()
    storage.get_virtual_device.return_value = existing
    storage.async_save_virtual_device = AsyncMock()
    source_manager = MagicMock()
    sensor_manager = MagicMock()
    sensor_manager.sensors = {}
    lifecycle_manager = MagicMock()
    lifecycle_manager.get_device_registry_id.return_value = "ha-device-1"

    updated = await async_add_virtual_entity(
        hass=hass,
        storage=storage,
        source_manager=source_manager,
        sensor_manager=sensor_manager,
        lifecycle_manager=lifecycle_manager,
        device_id=existing.id,
        device_class="power",
        aggregation="sum",
        name="Gesamtleistung",
    )

    assert updated.id == existing.id
    lifecycle_manager.get_device_registry_id.assert_called_once_with(
        updated.id
    )
    lifecycle_manager.async_ensure_device.assert_not_called()
    sensor_manager.add_entity.assert_called_once_with(
        device=updated,
        entity=updated.entities[0],
        values=source_manager.get_source_values.return_value,
        name="Gesamtleistung",
        device_id="ha-device-1",
    )
    lifecycle_manager.async_reconcile_device_entities.assert_called_once_with(
        updated
    )
    storage.async_save_virtual_device.assert_awaited_once_with(updated)


@pytest.mark.asyncio
async def test_update_virtual_entity_saves_updated_device() -> None:
    """Update a virtual entity and persist the result."""
    hass = MagicMock()

    existing = VirtualDevice(
        id="virtual_beleuchtung",
        label_ref="beleuchtung",
        entities=[
            VirtualEntity(
                id="virtual_beleuchtung_power",
                device_class="power",
                aggregation="sum",
            ),
        ],
    )

    updated = VirtualDevice(
        id="virtual_beleuchtung",
        label_ref="beleuchtung",
        entities=[
            VirtualEntity(
                id="virtual_beleuchtung_power",
                device_class="power",
                aggregation="avg",
            ),
        ],
    )

    storage = MagicMock()
    storage.get_virtual_device.return_value = existing
    storage.async_save_virtual_device = AsyncMock()

    source_manager = MagicMock()

    with patch(
        "custom_components.virtual_device.virtual_device_manager.update_virtual_entity",
        return_value=updated,
    ) as update_mock:
        result = await async_update_virtual_entity(
            hass=hass,
            storage=storage,
            source_manager=source_manager,
            device_id="virtual_beleuchtung",
            entity_id="virtual_beleuchtung_power",
            aggregation="avg",
        )

    source_manager.rebuild_virtual_device.assert_called_once_with(
        hass,
        updated,
    )

    assert result is updated
    update_mock.assert_called_once()
    storage.async_save_virtual_device.assert_awaited_once_with(updated)


@pytest.mark.asyncio
async def test_delete_virtual_entity_saves_updated_device() -> None:
    """Delete a virtual entity and persist the result."""
    hass = MagicMock()

    existing = VirtualDevice(
        id="virtual_beleuchtung",
        label_ref="beleuchtung",
        entities=[
            VirtualEntity(
                id="virtual_beleuchtung_power",
                device_class="power",
                aggregation="sum",
            ),
        ],
    )

    updated = VirtualDevice(
        id="virtual_beleuchtung",
        label_ref="beleuchtung",
    )

    storage = MagicMock()
    storage.get_virtual_device.return_value = existing
    storage.async_save_virtual_device = AsyncMock()

    source_manager = MagicMock()

    with patch(
        "custom_components.virtual_device.virtual_device_manager.delete_virtual_entity",
        return_value=updated,
    ) as delete_mock:
        result = await async_delete_virtual_entity(
            hass=hass,
            storage=storage,
            source_manager=source_manager,
            device_id="virtual_beleuchtung",
            entity_id="virtual_beleuchtung_power",
        )

    source_manager.rebuild_virtual_device.assert_called_once_with(
        hass,
        updated,
    )

    assert result is updated
    delete_mock.assert_called_once()
    storage.async_save_virtual_device.assert_awaited_once_with(updated)


@pytest.mark.asyncio
async def test_add_virtual_entity_rejects_unknown_device() -> None:
    """Reject adding an entity to an unknown device."""
    hass = MagicMock()

    storage = MagicMock()
    storage.get_virtual_device.return_value = None

    source_manager = MagicMock()
    sensor_manager = MagicMock()

    with pytest.raises(
        ValueError,
        match="does not exist",
    ):
        await async_add_virtual_entity(
            hass=hass,
            storage=storage,
            source_manager=source_manager,
            sensor_manager=sensor_manager,
            device_id="unknown-device",
            device_class="power",
            aggregation="sum",
        )
