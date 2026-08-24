"""Tests for the Virtual Device Manager WebSocket API."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.virtual_device.const import (
    AGGREGATIONS,
    SUPPORTED_DEVICE_CLASSES,
)
from custom_components.virtual_device.models import (
    VirtualDevice,
    VirtualEntity,
)
from custom_components.virtual_device.websocket import (
    _serialize_virtual_devices,
    async_register_websocket_commands,
)


@pytest.mark.asyncio
async def test_get_virtual_devices_websocket_command_is_registered() -> None:
    """Register the get_virtual_devices WebSocket command."""
    hass = MagicMock()
    storage = MagicMock()
    source_manager = MagicMock()
    sensor_manager = MagicMock()

    with patch(
        "custom_components.virtual_device.websocket.websocket_api.async_register_command"
    ) as register_mock:
        await async_register_websocket_commands(
            hass,
            storage,
            source_manager,
            sensor_manager,
        )

    registered_handlers = [call.args[1] for call in register_mock.call_args_list]

    assert any(
        handler.__name__ == "handle_get_virtual_devices"
        for handler in registered_handlers
    )


@pytest.mark.asyncio
async def test_get_entity_config_websocket_command_is_registered() -> None:
    """Register the get_entity_config WebSocket command."""
    hass = MagicMock()
    storage = MagicMock()
    source_manager = MagicMock()
    sensor_manager = MagicMock()

    with patch(
        "custom_components.virtual_device.websocket.websocket_api.async_register_command"
    ) as register_mock:
        await async_register_websocket_commands(
            hass,
            storage,
            source_manager,
            sensor_manager,
        )

    registered_handlers = [call.args[1] for call in register_mock.call_args_list]

    assert any(
        handler.__name__ == "handle_get_entity_config"
        for handler in registered_handlers
    )


@pytest.mark.asyncio
async def test_history_sync_command_requires_explicit_manager_registration() -> None:
    """Register the manual history command only when its manager is available."""
    with patch(
        "custom_components.virtual_device.websocket.websocket_api.async_register_command"
    ) as register_mock:
        await async_register_websocket_commands(
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            history_sync_manager=MagicMock(),
        )

    registered_handlers = [call.args[1] for call in register_mock.call_args_list]
    assert any(
        handler.__name__ == "handle_history_sync" for handler in registered_handlers
    )


@pytest.mark.asyncio
async def test_get_entity_config_websocket_returns_configuration() -> None:
    """Return supported device classes and aggregations."""
    hass = MagicMock()
    storage = MagicMock()
    connection = MagicMock()
    source_manager = MagicMock()
    sensor_manager = MagicMock()

    with patch(
        "custom_components.virtual_device.websocket.websocket_api.async_register_command"
    ) as register_mock:
        await async_register_websocket_commands(
            hass,
            storage,
            source_manager,
            sensor_manager,
        )

    handler = next(
        handler
        for handler in (call.args[1] for call in register_mock.call_args_list)
        if handler.__name__ == "handle_get_entity_config"
    )

    await handler.__wrapped__(
        hass=hass,
        connection=connection,
        msg={"id": 42},
    )

    result = connection.send_result.call_args.args[1]

    assert result["device_classes"] == list(SUPPORTED_DEVICE_CLASSES)
    assert result["aggregations"] == list(AGGREGATIONS)


def test_serialize_virtual_devices() -> None:
    """Serialize stored virtual devices for the frontend."""
    storage = MagicMock()

    entity = MagicMock()
    entity.id = "entity-energie"
    entity.device_class = "energy"
    entity.aggregation = "sum"
    entity.unit = "kWh"

    device = MagicMock()
    device.id = "virtual-energie"
    device.label_ref = "label-id-energie"
    device.entities = [entity]

    storage.get_virtual_devices.return_value = [device]

    result = _serialize_virtual_devices(storage)

    assert result == [
        {
            "id": "virtual-energie",
            "label_ref": "label-id-energie",
            "entities": [
                {
                    "id": "entity-energie",
                    "device_class": "energy",
                    "aggregation": "sum",
                    "name": "energy",
                }
            ],
            "name": None,
        }
    ]


@pytest.mark.asyncio
async def test_delete_virtual_device_websocket_command_is_registered() -> None:
    """Register the delete_virtual_device WebSocket command."""
    hass = MagicMock()
    storage = MagicMock()
    source_manager = MagicMock()
    sensor_manager = MagicMock()

    with patch(
        "custom_components.virtual_device.websocket.websocket_api.async_register_command"
    ) as register_mock:
        await async_register_websocket_commands(
            hass,
            storage,
            source_manager,
            sensor_manager,
        )

    registered_handlers = [call.args[1] for call in register_mock.call_args_list]

    assert any(
        handler.__name__ == "handle_delete_virtual_device"
        for handler in registered_handlers
    )


@pytest.mark.asyncio
async def test_delete_virtual_device_websocket_deletes_device() -> None:
    """Delete a virtual device through the WebSocket."""
    hass = MagicMock()
    storage = MagicMock()
    connection = MagicMock()
    source_manager = MagicMock()
    sensor_manager = MagicMock()

    with patch(
        "custom_components.virtual_device.websocket.websocket_api.async_register_command"
    ) as register_mock:
        await async_register_websocket_commands(
            hass,
            storage,
            source_manager,
            sensor_manager,
        )

    handler = next(
        handler
        for handler in (call.args[1] for call in register_mock.call_args_list)
        if handler.__name__ == "handle_delete_virtual_device"
    )

    with patch(
        "custom_components.virtual_device.websocket.async_delete_virtual_device",
        new_callable=AsyncMock,
    ) as delete_mock:
        await handler.__wrapped__(
            hass=hass,
            connection=connection,
            msg={
                "id": 42,
                "device_id": "virtual-energie",
            },
        )

    delete_mock.assert_awaited_once_with(
        hass=hass,
        storage=storage,
        device_id="virtual-energie",
    )

    connection.send_result.assert_called_once_with(
        42,
        {},
    )


@pytest.mark.asyncio
async def test_update_virtual_device_websocket_command_is_registered() -> None:
    """Register the update_virtual_device WebSocket command."""
    hass = MagicMock()
    storage = MagicMock()
    source_manager = MagicMock()
    sensor_manager = MagicMock()

    with patch(
        "custom_components.virtual_device.websocket.websocket_api.async_register_command"
    ) as register_mock:
        await async_register_websocket_commands(
            hass,
            storage,
            source_manager,
            sensor_manager,
        )

    registered_handlers = [call.args[1] for call in register_mock.call_args_list]

    assert any(
        handler.__name__ == "handle_update_virtual_device"
        for handler in registered_handlers
    )


@pytest.mark.asyncio
async def test_update_virtual_device_websocket_updates_device() -> None:
    """Update a virtual device through the WebSocket."""
    hass = MagicMock()
    storage = MagicMock()
    connection = MagicMock()
    source_manager = MagicMock()
    sensor_manager = MagicMock()

    with patch(
        "custom_components.virtual_device.websocket.websocket_api.async_register_command"
    ) as register_mock:
        await async_register_websocket_commands(
            hass,
            storage,
            source_manager,
            sensor_manager,
        )

    handler = next(
        handler
        for handler in (call.args[1] for call in register_mock.call_args_list)
        if handler.__name__ == "handle_update_virtual_device"
    )

    updated_device = VirtualDevice(
        id="virtual-energie",
        label_ref="label-id-heizung",
    )

    with patch(
        "custom_components.virtual_device.websocket.async_update_virtual_device",
        new_callable=AsyncMock,
        return_value=updated_device,
    ) as update_mock:
        await handler.__wrapped__(
            hass=hass,
            connection=connection,
            msg={
                "id": 42,
                "device_id": "virtual-energie",
                "name": "Haus Heizung",
                "confirm_physical_name_conflict": False,
            },
        )

    update_mock.assert_awaited_once_with(
        hass=hass,
        storage=storage,
        device_id="virtual-energie",
        name="Haus Heizung",
        confirm_physical_name_conflict=False,
    )

    connection.send_result.assert_called_once_with(
        42,
        {
            "device": {
                "id": "virtual-energie",
                "label_ref": "label-id-heizung",
                "entities": [],
                "name": None,
            }
        },
    )


@pytest.mark.asyncio
async def test_add_virtual_entity_websocket_command_is_registered() -> None:
    """Register the add_virtual_entity WebSocket command."""
    hass = MagicMock()
    storage = MagicMock()
    source_manager = MagicMock()
    sensor_manager = MagicMock()

    with patch(
        "custom_components.virtual_device.websocket.websocket_api.async_register_command"
    ) as register_mock:
        await async_register_websocket_commands(
            hass,
            storage,
            source_manager,
            sensor_manager,
        )

    registered_handlers = [call.args[1] for call in register_mock.call_args_list]

    assert any(
        handler.__name__ == "handle_add_virtual_entity"
        for handler in registered_handlers
    )


@pytest.mark.asyncio
async def test_add_virtual_entity_websocket_adds_entity() -> None:
    """Add a virtual entity through the WebSocket."""
    hass = MagicMock()
    storage = MagicMock()
    connection = MagicMock()
    source_manager = MagicMock()
    sensor_manager = MagicMock()

    with patch(
        "custom_components.virtual_device.websocket.websocket_api.async_register_command"
    ) as register_mock:
        await async_register_websocket_commands(
            hass,
            storage,
            source_manager,
            sensor_manager,
        )

    handler = next(
        handler
        for handler in (call.args[1] for call in register_mock.call_args_list)
        if handler.__name__ == "handle_add_virtual_entity"
    )

    updated_device = VirtualDevice(
        id="virtual-energie",
        label_ref="label-id-energie",
        entities=[
            VirtualEntity(
                id="virtual-energie_power",
                device_class="power",
                aggregation="sum",
            ),
        ],
    )

    with patch(
        "custom_components.virtual_device.websocket.async_add_virtual_entity",
        new_callable=AsyncMock,
        return_value=updated_device,
    ) as add_mock:
        await handler.__wrapped__(
            hass=hass,
            connection=connection,
            msg={
                "id": 42,
                "device_id": "virtual-energie",
                "device_class": "power",
                "aggregation": "sum",
                "name": "Gesamtleistung",
            },
        )

    add_mock.assert_awaited_once_with(
        hass=hass,
        storage=storage,
        source_manager=source_manager,
        sensor_manager=sensor_manager,
        device_id="virtual-energie",
        device_class="power",
        aggregation="sum",
        name="Gesamtleistung",
    )

    connection.send_result.assert_called_once_with(
        42,
        {
            "device": {
                "id": "virtual-energie",
                "label_ref": "label-id-energie",
                "entities": [
                    {
                        "id": "virtual-energie_power",
                        "device_class": "power",
                        "aggregation": "sum",
                        "name": "power",
                    }
                ],
                "name": None,
            }
        },
    )


@pytest.mark.asyncio
async def test_update_virtual_entity_websocket_command_is_registered() -> None:
    """Register the update_virtual_entity WebSocket command."""
    hass = MagicMock()
    storage = MagicMock()
    source_manager = MagicMock()
    sensor_manager = MagicMock()

    with patch(
        "custom_components.virtual_device.websocket.websocket_api.async_register_command"
    ) as register_mock:
        await async_register_websocket_commands(
            hass,
            storage,
            source_manager,
            sensor_manager,
        )

    registered_handlers = [call.args[1] for call in register_mock.call_args_list]

    assert any(
        handler.__name__ == "handle_update_virtual_entity"
        for handler in registered_handlers
    )


@pytest.mark.asyncio
async def test_update_virtual_entity_websocket_updates_entity() -> None:
    """Update a virtual entity through the WebSocket."""
    hass = MagicMock()
    storage = MagicMock()
    connection = MagicMock()
    source_manager = MagicMock()
    sensor_manager = MagicMock()

    with patch(
        "custom_components.virtual_device.websocket.websocket_api.async_register_command"
    ) as register_mock:
        await async_register_websocket_commands(
            hass,
            storage,
            source_manager,
            sensor_manager,
        )

    handler = next(
        handler
        for handler in (call.args[1] for call in register_mock.call_args_list)
        if handler.__name__ == "handle_update_virtual_entity"
    )

    updated_device = VirtualDevice(
        id="virtual-energie",
        label_ref="label-id-energie",
        entities=[
            VirtualEntity(
                id="virtual-energie_power",
                device_class="power",
                aggregation="avg",
            ),
        ],
    )

    with patch(
        "custom_components.virtual_device.websocket.async_update_virtual_entity",
        new_callable=AsyncMock,
        return_value=updated_device,
    ) as update_mock:
        await handler.__wrapped__(
            hass=hass,
            connection=connection,
            msg={
                "id": 42,
                "device_id": "virtual-energie",
                "entity_id": "virtual-energie_power",
                "aggregation": "avg",
                "name": "Durchschnittsleistung",
            },
        )

    update_mock.assert_awaited_once_with(
        hass=hass,
        storage=storage,
        source_manager=source_manager,
        device_id="virtual-energie",
        entity_id="virtual-energie_power",
        aggregation="avg",
        name="Durchschnittsleistung",
    )

    connection.send_result.assert_called_once_with(
        42,
        {
            "device": {
                "id": "virtual-energie",
                "label_ref": "label-id-energie",
                "entities": [
                    {
                        "id": "virtual-energie_power",
                        "device_class": "power",
                        "aggregation": "avg",
                        "name": "power",
                    }
                ],
                "name": None,
            }
        },
    )


@pytest.mark.asyncio
async def test_delete_virtual_entity_websocket_command_is_registered() -> None:
    """Register the delete_virtual_entity WebSocket command."""
    hass = MagicMock()
    storage = MagicMock()
    source_manager = MagicMock()
    sensor_manager = MagicMock()

    with patch(
        "custom_components.virtual_device.websocket.websocket_api.async_register_command"
    ) as register_mock:
        await async_register_websocket_commands(
            hass,
            storage,
            source_manager,
            sensor_manager,
        )

    registered_handlers = [call.args[1] for call in register_mock.call_args_list]

    assert any(
        handler.__name__ == "handle_delete_virtual_entity"
        for handler in registered_handlers
    )


@pytest.mark.asyncio
async def test_delete_virtual_entity_websocket_deletes_entity() -> None:
    """Delete a virtual entity through the WebSocket."""
    hass = MagicMock()
    storage = MagicMock()
    connection = MagicMock()
    source_manager = MagicMock()
    sensor_manager = MagicMock()

    with patch(
        "custom_components.virtual_device.websocket.websocket_api.async_register_command"
    ) as register_mock:
        await async_register_websocket_commands(
            hass,
            storage,
            source_manager,
            sensor_manager,
        )

    handler = next(
        handler
        for handler in (call.args[1] for call in register_mock.call_args_list)
        if handler.__name__ == "handle_delete_virtual_entity"
    )

    updated_device = VirtualDevice(
        id="virtual-energie",
        label_ref="label-id-energie",
    )

    with patch(
        "custom_components.virtual_device.websocket.async_delete_virtual_entity",
        new_callable=AsyncMock,
        return_value=updated_device,
    ) as delete_mock:
        await handler.__wrapped__(
            hass=hass,
            connection=connection,
            msg={
                "id": 42,
                "device_id": "virtual-energie",
                "entity_id": "virtual-energie_power",
            },
        )

    delete_mock.assert_awaited_once_with(
        hass=hass,
        storage=storage,
        source_manager=source_manager,
        device_id="virtual-energie",
        entity_id="virtual-energie_power",
    )

    connection.send_result.assert_called_once_with(
        42,
        {
            "device": {
                "id": "virtual-energie",
                "label_ref": "label-id-energie",
                "entities": [],
                "name": None,
            }
        },
    )
