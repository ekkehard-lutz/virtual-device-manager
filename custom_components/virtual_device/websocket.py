"""WebSocket API for the Virtual Device Manager."""

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant

from .lifecycle import VirtualDeviceLifecycleManager
from .sensor import VirtualSensorManager
from .source_manager import SourceManager
from .storage import VirtualDeviceStorage
from .virtual_device_manager import (
    async_add_virtual_entity,
    async_delete_virtual_device,
    async_delete_virtual_entity,
    async_update_virtual_device,
    async_update_virtual_entity,
)


def _serialize_virtual_entity(entity) -> dict:
    """Serialize one virtual entity."""
    return {
        "id": entity.id,
        "device_class": entity.device_class,
        "aggregation": entity.aggregation,
        "unit": entity.unit,
        "name": entity.name,
    }


def _serialize_virtual_device(device) -> dict:
    """Serialize one virtual device."""
    return {
        "id": device.id,
        "label_ref": device.label_ref,
        "name": device.name,
        "entities": [_serialize_virtual_entity(entity) for entity in device.entities],
    }


def _serialize_virtual_devices(
    storage: VirtualDeviceStorage,
) -> list[dict]:
    """Serialize virtual devices for the WebSocket API."""
    return [
        _serialize_virtual_device(device) for device in storage.get_virtual_devices()
    ]


async def async_register_websocket_commands(
    hass: HomeAssistant,
    storage: VirtualDeviceStorage,
    source_manager: SourceManager,
    sensor_manager: VirtualSensorManager,
    lifecycle_manager: VirtualDeviceLifecycleManager | None = None,
) -> None:
    """Register Virtual Device Manager WebSocket commands."""

    @websocket_api.websocket_command(
        {
            "type": "virtual_device/get_virtual_devices",
        }
    )
    @websocket_api.async_response
    async def handle_get_virtual_devices(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict,
    ) -> None:
        """Return virtual devices."""
        connection.send_result(
            msg["id"],
            {
                "devices": _serialize_virtual_devices(
                    storage,
                ),
            },
        )

    websocket_api.async_register_command(
        hass,
        handle_get_virtual_devices,
    )

    @websocket_api.websocket_command(
        {
            "type": "virtual_device/delete_virtual_device",
            "device_id": str,
        }
    )
    @websocket_api.async_response
    async def handle_delete_virtual_device(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict,
    ) -> None:
        """Delete a virtual device."""
        kwargs = {
            "hass": hass,
            "storage": storage,
            "device_id": msg["device_id"],
        }

        if lifecycle_manager is not None:
            kwargs["source_manager"] = source_manager
            kwargs["lifecycle_manager"] = lifecycle_manager

        await async_delete_virtual_device(**kwargs)

        connection.send_result(
            msg["id"],
            {},
        )

    websocket_api.async_register_command(
        hass,
        handle_delete_virtual_device,
    )

    @websocket_api.websocket_command(
        {
            "type": "virtual_device/update_virtual_device",
            "device_id": str,
            "name": str,
            "label_ref": str,
            "confirm_physical_name_conflict": bool,
        }
    )
    @websocket_api.async_response
    async def handle_update_virtual_device(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict,
    ) -> None:
        """Update a virtual device."""
        kwargs = {
            "hass": hass,
            "storage": storage,
            "device_id": msg["device_id"],
            "name": msg["name"],
            "label_ref": msg["label_ref"],
            "confirm_physical_name_conflict": msg.get(
                "confirm_physical_name_conflict",
                False,
            ),
        }

        if lifecycle_manager is not None:
            kwargs["lifecycle_manager"] = lifecycle_manager

        updated_device = await async_update_virtual_device(**kwargs)

        connection.send_result(
            msg["id"],
            {
                "device": _serialize_virtual_device(
                    updated_device,
                ),
            },
        )

    websocket_api.async_register_command(
        hass,
        handle_update_virtual_device,
    )

    @websocket_api.websocket_command(
        {
            "type": "virtual_device/add_virtual_entity",
            "device_id": str,
            "device_class": str,
            "aggregation": str,
            "unit": str,
            "name": str,
        }
    )
    @websocket_api.async_response
    async def handle_add_virtual_entity(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict,
    ) -> None:
        """Add a virtual entity."""
        kwargs = {
            "hass": hass,
            "storage": storage,
            "source_manager": source_manager,
            "sensor_manager": sensor_manager,
            "device_id": msg["device_id"],
            "device_class": msg["device_class"],
            "aggregation": msg["aggregation"],
            "unit": msg["unit"],
            "name": msg.get("name"),
        }

        if lifecycle_manager is not None:
            kwargs["lifecycle_manager"] = lifecycle_manager

        updated_device = await async_add_virtual_entity(**kwargs)

        connection.send_result(
            msg["id"],
            {
                "device": _serialize_virtual_device(
                    updated_device,
                ),
            },
        )

    websocket_api.async_register_command(
        hass,
        handle_add_virtual_entity,
    )

    @websocket_api.websocket_command(
        {
            "type": "virtual_device/update_virtual_entity",
            "device_id": str,
            "entity_id": str,
            "device_class": str,
            "aggregation": str,
            "unit": str,
            "name": str,
        }
    )
    @websocket_api.async_response
    async def handle_update_virtual_entity(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict,
    ) -> None:
        """Update a virtual entity."""
        kwargs = {
            "hass": hass,
            "storage": storage,
            "source_manager": source_manager,
            "device_id": msg["device_id"],
            "entity_id": msg["entity_id"],
            "device_class": msg.get("device_class"),
            "aggregation": msg.get("aggregation"),
            "unit": msg.get("unit"),
            "name": msg.get("name"),
        }

        if lifecycle_manager is not None:
            kwargs["sensor_manager"] = sensor_manager

        updated_device = await async_update_virtual_entity(**kwargs)

        connection.send_result(
            msg["id"],
            {
                "device": _serialize_virtual_device(
                    updated_device,
                ),
            },
        )

    websocket_api.async_register_command(
        hass,
        handle_update_virtual_entity,
    )

    @websocket_api.websocket_command(
        {
            "type": "virtual_device/delete_virtual_entity",
            "device_id": str,
            "entity_id": str,
        }
    )
    @websocket_api.async_response
    async def handle_delete_virtual_entity(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict,
    ) -> None:
        """Delete a virtual entity."""
        kwargs = {
            "hass": hass,
            "storage": storage,
            "source_manager": source_manager,
            "device_id": msg["device_id"],
            "entity_id": msg["entity_id"],
        }

        if lifecycle_manager is not None:
            kwargs["lifecycle_manager"] = lifecycle_manager

        updated_device = await async_delete_virtual_entity(**kwargs)

        connection.send_result(
            msg["id"],
            {
                "device": _serialize_virtual_device(
                    updated_device,
                ),
            },
        )

    websocket_api.async_register_command(
        hass,
        handle_delete_virtual_entity,
    )
