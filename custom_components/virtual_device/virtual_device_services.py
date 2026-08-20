"""Home Assistant services for virtual devices."""

import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.helpers import service

from .const import DOMAIN
from .lifecycle import VirtualDeviceLifecycleManager
from .source_manager import SourceManager
from .storage import VirtualDeviceStorage
from .virtual_device_manager import (
    async_create_virtual_device,
    async_delete_virtual_device,
    async_update_virtual_device,
)


async def async_register_virtual_device_services(
    hass: HomeAssistant,
    storage: VirtualDeviceStorage,
    lifecycle_manager: VirtualDeviceLifecycleManager | None = None,
    source_manager: SourceManager | None = None,
) -> None:
    """Register virtual device services."""

    async def handle_create(call: service.ServiceCall) -> None:
        """Handle virtual device creation."""
        label_ref = call.data.get("label_ref")

        if not label_ref:
            raise ValueError("label_ref is required")

        kwargs = {
            "hass": hass,
            "storage": storage,
            "label_ref": label_ref,
            "name": call.data.get("name"),
        }

        if lifecycle_manager is not None:
            kwargs["lifecycle_manager"] = lifecycle_manager

        await async_create_virtual_device(**kwargs)

    async def handle_update(call: service.ServiceCall) -> None:
        """Handle virtual device update."""
        device_id = call.data.get("device_id")

        if not device_id:
            raise ValueError("device_id is required")

        kwargs = {
            "hass": hass,
            "storage": storage,
            "device_id": device_id,
            "name": call.data.get("name"),
            "label_ref": call.data.get("label_ref"),
        }

        if lifecycle_manager is not None:
            kwargs["lifecycle_manager"] = lifecycle_manager

        await async_update_virtual_device(**kwargs)

    async def handle_delete(call: service.ServiceCall) -> None:
        """Handle virtual device deletion."""
        device_id = call.data.get("device_id")

        if not device_id:
            raise ValueError("device_id is required")

        kwargs = {
            "hass": hass,
            "storage": storage,
            "device_id": device_id,
        }

        if source_manager is not None:
            kwargs["source_manager"] = source_manager

        if lifecycle_manager is not None:
            kwargs["lifecycle_manager"] = lifecycle_manager

        await async_delete_virtual_device(**kwargs)

    hass.services.async_register(
        DOMAIN,
        "create_virtual_device",
        handle_create,
        schema=vol.Schema(
            {
                vol.Required("label_ref"): str,
                vol.Optional("name"): str,
            }
        ),
    )

    hass.services.async_register(
        DOMAIN,
        "update_virtual_device",
        handle_update,
        schema=vol.Schema(
            {
                vol.Required("device_id"): str,
                vol.Optional("name"): str,
                vol.Optional("label_ref"): str,
            }
        ),
    )

    hass.services.async_register(
        DOMAIN,
        "delete_virtual_device",
        handle_delete,
        schema=vol.Schema(
            {
                vol.Required("device_id"): str,
            }
        ),
    )
