"""The Virtual Device Manager integration."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components import panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    PLATFORMS,
)
from .sensor import VirtualSensorManager
from .source_manager import SourceManager
from .storage import VirtualDeviceStorage
from .virtual_device_services import async_register_virtual_device_services
from .websocket import async_register_websocket_commands

type VirtualDeviceConfigEntry = ConfigEntry


async def async_setup(
    hass: HomeAssistant,
    config: dict,
) -> bool:
    """Set up the Virtual Device Manager integration."""

    hass.data.setdefault(DOMAIN, {})

    frontend_path = Path(__file__).parent / "frontend"

    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                "/api/virtual_device/frontend",
                str(frontend_path),
                False,
            )
        ]
    )

    await panel_custom.async_register_panel(
        hass,
        frontend_url_path="virtual-device",
        webcomponent_name="virtual-device-manager",
        sidebar_title="Virtual Device Manager",
        sidebar_icon="mdi:label-multiple",
        js_url="/api/virtual_device/frontend/virtual-devices.js",
        require_admin=True,
    )

    return True


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VirtualDeviceConfigEntry,
) -> bool:
    """Set up Virtual Device Manager from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    storage = VirtualDeviceStorage(hass)
    await storage.async_load()

    source_manager = SourceManager()
    sensor_manager = VirtualSensorManager()

    await async_register_virtual_device_services(
        hass,
        storage,
    )

    await async_register_websocket_commands(
        hass,
        storage,
        source_manager,
        sensor_manager,
    )

    hass.data[DOMAIN][entry.entry_id] = {
        "storage": storage,
        "source_manager": source_manager,
        "sensor_manager": sensor_manager,
    }

    await hass.config_entries.async_forward_entry_setups(
        entry,
        PLATFORMS,
    )

    await source_manager.async_start(hass)

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: VirtualDeviceConfigEntry,
) -> bool:
    """Unload a Virtual Device Manager config entry."""

    entry_data = hass.data[DOMAIN].pop(entry.entry_id, None)

    if entry_data is None:
        return True

    source_manager = entry_data.get("source_manager")

    if source_manager is not None:
        await source_manager.async_stop()

    return await hass.config_entries.async_unload_platforms(
        entry,
        PLATFORMS,
    )
