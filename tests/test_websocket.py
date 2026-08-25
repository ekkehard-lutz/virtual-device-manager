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


def test_serialize_virtual_devices_includes_runtime_source_counts() -> None:
    """Include current SourceManager relationships without persisting them."""
    storage = MagicMock()
    source_manager = MagicMock()
    storage.get_virtual_devices.return_value = [
        VirtualDevice(
            id="virtual-lighting",
            label_ref="lighting",
            entities=[
                VirtualEntity("virtual-lighting_power", "power", "sum"),
                VirtualEntity("virtual-lighting_energy", "energy", "sum"),
            ],
        )
    ]
    source_manager.get_sources.side_effect = lambda entity_id: (
        ["sensor.left", "sensor.right"] if entity_id == "virtual-lighting_power" else []
    )

    result = _serialize_virtual_devices(storage, source_manager=source_manager)

    assert result[0]["entities"][0]["source_count"] == 2
    assert result[0]["entities"][1]["source_count"] == 0


@pytest.mark.parametrize(
    ("registered_labels", "expected_missing"),
    [
        ({"label-original": MagicMock(name="Original")}, False),
        ({}, True),
    ],
)
def test_serialize_virtual_devices_derives_label_missing(
    registered_labels: dict, expected_missing: bool
) -> None:
    """Report whether the exact referenced label ID still exists."""
    entity = VirtualEntity("virtual-lighting_power", "power", "sum")
    device = VirtualDevice(
        id="virtual-lighting",
        label_ref="label-original",
        entities=[entity],
    )
    storage = MagicMock()
    storage.get_virtual_devices.return_value = [device]
    labels = MagicMock()
    labels.async_get_label.side_effect = registered_labels.get

    result = _serialize_virtual_devices(storage, labels=labels)

    assert result[0]["label_missing"] is expected_missing
    assert result[0]["label_ref"] == "label-original"
    assert device.label_ref == "label-original"
    assert device.entities == [entity]
    assert device.entities[0] is entity


def test_serialize_virtual_devices_does_not_relink_same_named_label() -> None:
    """A replacement label with the same name does not satisfy the old ID."""
    entity = VirtualEntity("virtual-test_power", "power", "sum")
    device = VirtualDevice(
        id="virtual-test",
        label_ref="deleted-label-id",
        entities=[entity],
    )
    storage = MagicMock()
    storage.get_virtual_devices.return_value = [device]
    labels = MagicMock()
    replacement = MagicMock()
    replacement.label_id = "new-label-id"
    replacement.name = "Test77"
    labels.labels = {replacement.label_id: replacement}
    labels.async_get_label.side_effect = labels.labels.get

    result = _serialize_virtual_devices(storage, labels=labels)

    assert result[0]["label_missing"] is True
    assert result[0]["label_ref"] == "deleted-label-id"
    assert device.entities == [entity]


async def _get_source_handler(storage, source_manager):
    """Register and return the source-details handler."""
    with patch(
        "custom_components.virtual_device.websocket.websocket_api.async_register_command"
    ) as register_mock:
        await async_register_websocket_commands(
            MagicMock(), storage, source_manager, MagicMock()
        )
    return next(
        call.args[1]
        for call in register_mock.call_args_list
        if call.args[1].__name__ == "handle_get_source_entities"
    )


@pytest.mark.asyncio
async def test_get_source_entities_resolves_registry_names() -> None:
    """Resolve entity and preferred device names from Home Assistant registries."""
    device = VirtualDevice(
        id="virtual-lighting",
        label_ref="lighting",
        entities=[VirtualEntity("virtual-lighting_power", "power", "sum")],
    )
    storage = MagicMock()
    storage.get_virtual_device.return_value = device
    source_manager = MagicMock()
    source_manager.get_sources.return_value = ["sensor.left", "sensor.no_device"]
    handler = await _get_source_handler(storage, source_manager)

    left = MagicMock(name="left_entry")
    left.name = "Power"
    left.device_id = "device-left"
    no_device = MagicMock(name="no_device_entry")
    no_device.name = None
    no_device.device_id = None
    entity_reg = MagicMock()
    entity_reg.async_get.side_effect = lambda entity_id: {
        "sensor.left": left,
        "sensor.no_device": no_device,
    }[entity_id]
    physical_device = MagicMock()
    physical_device.name_by_user = "Kitchen left"
    physical_device.name = "Default left"
    device_reg = MagicMock()
    device_reg.async_get.return_value = physical_device
    hass = MagicMock()
    fallback_state = MagicMock()
    fallback_state.name = "Visible fallback"
    hass.states.get.side_effect = lambda entity_id: (
        fallback_state if entity_id == "sensor.no_device" else None
    )
    connection = MagicMock()

    with (
        patch(
            "custom_components.virtual_device.websocket.entity_registry.async_get",
            return_value=entity_reg,
        ),
        patch(
            "custom_components.virtual_device.websocket.device_registry.async_get",
            return_value=device_reg,
        ),
    ):
        await handler.__wrapped__(
            hass=hass,
            connection=connection,
            msg={
                "id": 7,
                "device_id": device.id,
                "entity_id": device.entities[0].id,
            },
        )

    result = connection.send_result.call_args.args[1]
    assert {source["entity_id"] for source in result["sources"]} == {
        "sensor.left",
        "sensor.no_device",
    }
    by_id = {source["entity_id"]: source for source in result["sources"]}
    assert by_id["sensor.left"]["entity_name"] == "Power"
    assert by_id["sensor.left"]["device_name"] == "Kitchen left"
    assert by_id["sensor.no_device"]["entity_name"] == "Visible fallback"
    assert by_id["sensor.no_device"]["device_name"] == "—"


@pytest.mark.asyncio
@pytest.mark.parametrize("unknown", ["device", "entity"])
async def test_get_source_entities_rejects_unknown_targets(unknown: str) -> None:
    """Return not_found for an unknown device or unrelated virtual entity."""
    storage = MagicMock()
    storage.get_virtual_device.return_value = (
        None
        if unknown == "device"
        else VirtualDevice(
            id="virtual-lighting",
            label_ref="lighting",
            entities=[VirtualEntity("virtual-lighting_power", "power", "sum")],
        )
    )
    handler = await _get_source_handler(storage, MagicMock())
    connection = MagicMock()

    await handler.__wrapped__(
        hass=MagicMock(),
        connection=connection,
        msg={
            "id": 8,
            "device_id": "missing" if unknown == "device" else "virtual-lighting",
            "entity_id": "missing",
        },
    )

    assert connection.send_error.call_args.args[:2] == (8, "not_found")


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
