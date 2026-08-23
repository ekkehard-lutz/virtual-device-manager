"""Tests for Virtual Device Manager storage."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.virtual_device.models import (
    VirtualDevice,
    VirtualEntity,
)
from custom_components.virtual_device.storage import (
    VirtualDeviceStorage,
)


@pytest.mark.asyncio
async def test_virtual_device_save_and_load() -> None:
    """Test saving and loading a virtual device."""
    hass = MagicMock()
    storage = VirtualDeviceStorage(hass)

    storage.async_save = AsyncMock()

    entity = VirtualEntity(
        id="test-entity",
        device_class="power",
        aggregation="sum",
    )

    device = VirtualDevice(
        id="test-device",
        label_ref="label-id-energie",
        entities=[entity],
    )

    await storage.async_save_virtual_device(device)

    loaded = storage.get_virtual_device("test-device")

    assert loaded is not None
    assert loaded.id == "test-device"
    assert loaded.label_ref == "label-id-energie"

    assert len(loaded.entities) == 1
    assert loaded.entities[0].id == "test-entity"
    assert loaded.entities[0].device_class == "power"
    assert loaded.entities[0].aggregation == "sum"
    assert not hasattr(loaded.entities[0], "unit")

    storage.async_save.assert_awaited_once()


@pytest.mark.asyncio
async def test_virtual_device_update_and_save() -> None:
    """Test updating and saving an existing virtual device."""
    hass = MagicMock()
    storage = VirtualDeviceStorage(hass)
    storage.async_save = AsyncMock()

    original = VirtualDevice(
        id="test-device",
        label_ref="label-id-energie",
    )

    await storage.async_save_virtual_device(original)

    updated = VirtualDevice(
        id="test-device",
        label_ref="label-id-energie",
    )

    await storage.async_save_virtual_device(updated)

    loaded = storage.get_virtual_device("test-device")

    assert loaded is not None
    assert loaded.id == "test-device"
    assert loaded.label_ref == "label-id-energie"

    assert len(storage.get_virtual_devices()) == 1
    assert storage.async_save.await_count == 2


@pytest.mark.asyncio
async def test_load_stored_virtual_devices() -> None:
    """Test loading stored virtual devices from Home Assistant storage."""
    hass = MagicMock()
    storage = VirtualDeviceStorage(hass)

    storage._store = MagicMock()
    storage._store.async_load = AsyncMock(
        return_value={
            "version": 1,
            "virtual_devices": {
                "device-1": {
                    "label_ref": "label-id-energie",
                    "entities": {
                        "entity-1": {
                            "device_class": "power",
                            "aggregation": "sum",
                            "unit": "kW",
                        },
                    },
                },
            },
        }
    )

    await storage.async_load()

    assert storage._data["version"] == 1

    device = storage.get_virtual_device("device-1")

    assert device is not None
    assert device.id == "device-1"
    assert device.label_ref == "label-id-energie"

    assert len(device.entities) == 1
    assert device.entities[0].id == "entity-1"
    assert device.entities[0].device_class == "power"
    assert device.entities[0].aggregation == "sum"
    assert not hasattr(device.entities[0], "unit")


@pytest.mark.asyncio
async def test_load_empty_storage() -> None:
    """Test loading when no storage exists yet."""
    hass = MagicMock()
    storage = VirtualDeviceStorage(hass)

    storage._store = MagicMock()
    storage._store.async_load = AsyncMock(
        return_value=None,
    )

    await storage.async_load()

    assert storage.get_virtual_devices() == []


@pytest.mark.asyncio
async def test_multiple_virtual_devices() -> None:
    """Test storing multiple virtual devices."""
    hass = MagicMock()
    storage = VirtualDeviceStorage(hass)

    storage.async_save = AsyncMock()

    device1 = VirtualDevice(
        id="device-1",
        label_ref="label-id-energie",
    )

    device2 = VirtualDevice(
        id="device-2",
        label_ref="label-id-beleuchtung",
    )

    await storage.async_save_virtual_device(device1)
    await storage.async_save_virtual_device(device2)

    devices = storage.get_virtual_devices()

    assert len(devices) == 2

    assert storage.get_virtual_device("device-1") is not None
    assert storage.get_virtual_device("device-2") is not None


@pytest.mark.asyncio
async def test_get_missing_virtual_device() -> None:
    """Test requesting a virtual device that does not exist."""
    hass = MagicMock()
    storage = VirtualDeviceStorage(hass)

    assert storage.get_virtual_device("does-not-exist") is None


@pytest.mark.asyncio
async def test_delete_virtual_device() -> None:
    """Test deleting a virtual device."""
    hass = MagicMock()
    storage = VirtualDeviceStorage(hass)

    storage.async_save = AsyncMock()

    device = VirtualDevice(
        id="device-1",
        label_ref="label-id-energie",
    )

    await storage.async_save_virtual_device(device)

    assert storage.get_virtual_device("device-1") is not None

    await storage.async_delete_virtual_device("device-1")

    assert storage.get_virtual_device("device-1") is None
    assert storage.get_virtual_devices() == []

    assert storage.async_save.await_count == 2


@pytest.mark.asyncio
async def test_delete_missing_virtual_device() -> None:
    """Test deleting a virtual device that does not exist."""
    hass = MagicMock()
    storage = VirtualDeviceStorage(hass)

    storage.async_save = AsyncMock()

    await storage.async_delete_virtual_device(
        "does-not-exist",
    )

    storage.async_save.assert_awaited_once()


@pytest.mark.asyncio
async def test_virtual_device_without_entities() -> None:
    """Test storing a virtual device without virtual entities."""
    hass = MagicMock()
    storage = VirtualDeviceStorage(hass)

    storage.async_save = AsyncMock()

    device = VirtualDevice(
        id="device-1",
        label_ref="label-id-licht",
    )

    await storage.async_save_virtual_device(device)

    loaded = storage.get_virtual_device("device-1")

    assert loaded is not None
    assert loaded.label_ref == "label-id-licht"
    assert loaded.entities == []
