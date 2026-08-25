"""WebSocket API for the Virtual Device Manager."""

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry, entity_registry

from .const import AGGREGATIONS, SUPPORTED_DEVICE_CLASSES
from .history.manager import HistorySyncBusyError, HistorySyncManager
from .lifecycle import VirtualDeviceLifecycleManager
from .sensor import VirtualSensorManager
from .source_manager import SourceManager
from .storage import VirtualDeviceStorage
from .translation import panel_translations
from .virtual_device_manager import (
    async_add_virtual_entity,
    async_delete_virtual_device,
    async_delete_virtual_entity,
    async_update_virtual_device,
    async_update_virtual_entity,
)


def _serialize_virtual_entity(
    entity,
    lifecycle_manager: VirtualDeviceLifecycleManager | None = None,
    source_manager: SourceManager | None = None,
) -> dict:
    """Serialize one virtual entity."""
    result = {
        "id": entity.id,
        "device_class": entity.device_class,
        "aggregation": entity.aggregation,
    }

    if lifecycle_manager is not None:
        result["name"] = lifecycle_manager.get_entity_name(entity.id)
    else:
        result["name"] = entity.device_class

    if source_manager is not None:
        result["source_count"] = len(source_manager.get_sources(entity.id))

    return result


def _serialize_virtual_device(
    device,
    lifecycle_manager: VirtualDeviceLifecycleManager | None = None,
    source_manager: SourceManager | None = None,
) -> dict:
    """Serialize one virtual device."""
    result = {
        "id": device.id,
        "label_ref": device.label_ref,
        "entities": [
            _serialize_virtual_entity(entity, lifecycle_manager, source_manager)
            for entity in device.entities
        ],
    }

    if lifecycle_manager is not None:
        result["name"] = lifecycle_manager.get_device_name(device.id, device.label_ref)
    else:
        result["name"] = None

    return result


def _serialize_virtual_devices(
    storage: VirtualDeviceStorage,
    lifecycle_manager: VirtualDeviceLifecycleManager | None = None,
    source_manager: SourceManager | None = None,
) -> list[dict]:
    """Serialize virtual devices for the WebSocket API."""
    return [
        _serialize_virtual_device(device, lifecycle_manager, source_manager)
        for device in storage.get_virtual_devices()
    ]


async def async_register_websocket_commands(
    hass: HomeAssistant,
    storage: VirtualDeviceStorage,
    source_manager: SourceManager,
    sensor_manager: VirtualSensorManager,
    lifecycle_manager: VirtualDeviceLifecycleManager | None = None,
    history_sync_manager: HistorySyncManager | None = None,
    translation_resources: dict[str, dict] | None = None,
) -> None:
    """Register Virtual Device Manager WebSocket commands."""

    @websocket_api.websocket_command(
        {"type": "virtual_device/get_translations", "language": str}
    )
    @websocket_api.async_response
    async def handle_get_translations(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict,
    ) -> None:
        """Return panel translations for the active Home Assistant language."""
        connection.send_result(
            msg["id"],
            panel_translations(translation_resources or {}, msg.get("language")),
        )

    websocket_api.async_register_command(hass, handle_get_translations)

    @websocket_api.websocket_command(
        {
            "type": "virtual_device/get_entity_config",
        }
    )
    @websocket_api.async_response
    async def handle_get_entity_config(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict,
    ) -> None:
        """Return virtual entity configuration options."""
        device_classes = list(SUPPORTED_DEVICE_CLASSES)

        connection.send_result(
            msg["id"],
            {
                "device_classes": device_classes,
                "aggregations": list(AGGREGATIONS),
            },
        )

    websocket_api.async_register_command(
        hass,
        handle_get_entity_config,
    )

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
                    lifecycle_manager,
                    source_manager,
                ),
            },
        )

    websocket_api.async_register_command(
        hass,
        handle_get_virtual_devices,
    )

    @websocket_api.websocket_command(
        {
            "type": "virtual_device/get_source_entities",
            "device_id": str,
            "entity_id": str,
        }
    )
    @websocket_api.async_response
    async def handle_get_source_entities(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict,
    ) -> None:
        """Return registry details for the current physical source entities."""
        device = storage.get_virtual_device(msg["device_id"])
        if device is None:
            connection.send_error(msg["id"], "not_found", "Virtual device not found")
            return

        if not any(entity.id == msg["entity_id"] for entity in device.entities):
            connection.send_error(msg["id"], "not_found", "Virtual entity not found")
            return

        entity_reg = entity_registry.async_get(hass)
        device_reg = device_registry.async_get(hass)
        sources = []

        for source_entity_id in source_manager.get_sources(msg["entity_id"]):
            registry_entry = entity_reg.async_get(source_entity_id)
            state = hass.states.get(source_entity_id)
            entity_name = (
                getattr(registry_entry, "name", None)
                or getattr(state, "name", None)
                or source_entity_id
            )

            registry_device = None
            if registry_entry is not None and registry_entry.device_id:
                registry_device = device_reg.async_get(registry_entry.device_id)
            device_name = (
                getattr(registry_device, "name_by_user", None)
                or getattr(registry_device, "name", None)
                or "—"
            )
            sources.append(
                {
                    "entity_id": source_entity_id,
                    "entity_name": entity_name,
                    "device_name": device_name,
                }
            )

        sources.sort(
            key=lambda source: (
                source["device_name"].casefold(),
                source["entity_name"].casefold(),
                source["entity_id"],
            )
        )
        connection.send_result(
            msg["id"],
            {
                "device_id": device.id,
                "entity_id": msg["entity_id"],
                "sources": sources,
            },
        )

    websocket_api.async_register_command(hass, handle_get_source_entities)

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
                    lifecycle_manager,
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
                    lifecycle_manager,
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
            "aggregation": msg.get("aggregation"),
            "name": msg.get("name"),
        }

        if "device_class" in msg:
            kwargs["device_class"] = msg["device_class"]

        if lifecycle_manager is not None:
            kwargs["sensor_manager"] = sensor_manager
            kwargs["lifecycle_manager"] = lifecycle_manager

        updated_device = await async_update_virtual_entity(**kwargs)

        connection.send_result(
            msg["id"],
            {
                "device": _serialize_virtual_device(
                    updated_device,
                    lifecycle_manager,
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
                    lifecycle_manager,
                ),
            },
        )

    websocket_api.async_register_command(
        hass,
        handle_delete_virtual_entity,
    )

    if history_sync_manager is None:
        return

    @websocket_api.require_admin
    @websocket_api.websocket_command(
        {
            "type": "virtual_device/history_sync",
            "device_id": str,
        }
    )
    @websocket_api.async_response
    async def handle_history_sync(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict,
    ) -> None:
        """Run the only explicit entry point for history synchronization."""
        device = storage.get_virtual_device(msg["device_id"])
        if device is None:
            connection.send_error(msg["id"], "not_found", "Virtual device not found")
            return
        try:
            result = await history_sync_manager.async_sync(device)
        except HistorySyncBusyError as err:
            connection.send_error(msg["id"], "busy", str(err))
            return
        connection.send_result(
            msg["id"],
            {
                "device_id": result.device_id,
                "status": result.status,
                "persistence_mode": result.persistence_mode,
                "limitations": list(result.limitations),
                "entities": [
                    {
                        "entity_id": item.virtual_entity_id,
                        "status": item.status,
                        "reason": item.reason,
                        "reason_code": item.reason_code,
                        "range_start": (
                            item.range_start.isoformat() if item.range_start else None
                        ),
                        "range_end": (
                            item.range_end.isoformat() if item.range_end else None
                        ),
                        "resolutions": list(item.resolutions),
                        "hourly_slots_upserted": item.hourly_slots_upserted,
                    }
                    for item in result.entities
                ],
            },
        )

    websocket_api.async_register_command(hass, handle_history_sync)
