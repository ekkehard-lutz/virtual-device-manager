"""Tests for Virtual Device Manager integration setup."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.virtual_device import (
    async_setup,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.virtual_device.const import (
    DOMAIN,
    PLATFORMS,
)


@pytest.mark.asyncio
async def test_setup_registers_frontend_static_path() -> None:
    """Test frontend static path registration."""
    hass = MagicMock()
    hass.data = {}
    hass.http.async_register_static_paths = AsyncMock()

    result = await async_setup(hass, {})

    assert result is True

    hass.http.async_register_static_paths.assert_awaited_once()

    static_paths = (
        hass.http.async_register_static_paths.await_args.args[0]
    )

    assert len(static_paths) == 1

    assert (
        static_paths[0].url_path
        == "/api/virtual_device/frontend"
    )

    assert static_paths[0].cache_headers is False


@pytest.mark.asyncio
async def test_setup_registers_frontend_panel(
    monkeypatch,
) -> None:
    """Test frontend panel registration."""
    hass = MagicMock()
    hass.data = {}
    hass.http.async_register_static_paths = AsyncMock()

    panel_mock = AsyncMock()

    monkeypatch.setattr(
        "custom_components.virtual_device.panel_custom.async_register_panel",
        panel_mock,
    )

    result = await async_setup(hass, {})

    assert result is True

    panel_mock.assert_awaited_once_with(
        hass,
        frontend_url_path="virtual-device",
        webcomponent_name="virtual-device-manager",
        sidebar_title="Virtual Device Manager",
        sidebar_icon="mdi:label-multiple",
        js_url=(
            "/api/virtual_device/frontend/"
            "virtual-devices.js"
        ),
        require_admin=True,
    )


@pytest.mark.asyncio
async def test_setup_entry(
    monkeypatch,
) -> None:
    """Test setting up a Virtual Device Manager entry."""
    hass = MagicMock()
    hass.data = {}

    entry = MagicMock()
    entry.entry_id = "test_entry"

    storage = MagicMock()
    storage.async_load = AsyncMock()

    source_manager = MagicMock()
    source_manager.async_start = AsyncMock()

    services_mock = AsyncMock()
    websocket_mock = AsyncMock()

    monkeypatch.setattr(
        "custom_components.virtual_device.VirtualDeviceStorage",
        lambda hass: storage,
    )

    monkeypatch.setattr(
        "custom_components.virtual_device.SourceManager",
        lambda: source_manager,
    )

    monkeypatch.setattr(
        "custom_components.virtual_device."
        "async_register_virtual_device_services",
        services_mock,
    )

    monkeypatch.setattr(
        "custom_components.virtual_device."
        "async_register_websocket_commands",
        websocket_mock,
    )

    hass.config_entries.async_forward_entry_setups = (
        AsyncMock()
    )

    result = await async_setup_entry(
        hass,
        entry,
    )

    assert result is True

    storage.async_load.assert_awaited_once()

    services_mock.assert_awaited_once_with(
        hass,
        storage,
    )

    sensor_manager = hass.data[DOMAIN][entry.entry_id]["sensor_manager"]

    websocket_mock.assert_awaited_once_with(
        hass,
        storage,
        source_manager,
        sensor_manager,
    )

    hass.config_entries.async_forward_entry_setups.assert_awaited_once_with(
        entry,
        PLATFORMS,
    )

    source_manager.async_start.assert_awaited_once_with(
        hass,
    )

    assert DOMAIN in hass.data
    assert entry.entry_id in hass.data[DOMAIN]

    entry_data = hass.data[DOMAIN][entry.entry_id]

    assert entry_data["storage"] is storage
    assert entry_data["source_manager"] is source_manager


@pytest.mark.asyncio
async def test_unload_entry(
    monkeypatch,
) -> None:
    """Test unloading a Virtual Device Manager entry."""
    hass = MagicMock()

    entry = MagicMock()
    entry.entry_id = "test_entry"

    source_manager = MagicMock()
    source_manager.async_stop = AsyncMock()

    hass.data = {
        DOMAIN: {
            entry.entry_id: {
                "storage": MagicMock(),
                "source_manager": source_manager,
            }
        }
    }

    hass.config_entries.async_unload_platforms = (
        AsyncMock(return_value=True)
    )

    result = await async_unload_entry(
        hass,
        entry,
    )

    assert result is True

    source_manager.async_stop.assert_awaited_once()

    hass.config_entries.async_unload_platforms.assert_awaited_once_with(
        entry,
        PLATFORMS,
    )

    assert entry.entry_id not in hass.data[DOMAIN]


@pytest.mark.asyncio
async def test_unload_missing_entry() -> None:
    """Test unloading an entry that is no longer registered."""
    hass = MagicMock()

    entry = MagicMock()
    entry.entry_id = "missing_entry"

    hass.data = {
        DOMAIN: {},
    }

    result = await async_unload_entry(
        hass,
        entry,
    )

    assert result is True
