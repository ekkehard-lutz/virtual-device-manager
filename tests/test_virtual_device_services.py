"""Tests for virtual device Home Assistant services."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import voluptuous as vol

from custom_components.virtual_device.virtual_device_services import (
    async_register_virtual_device_services,
)


@pytest.mark.asyncio
async def test_virtual_device_services_are_registered() -> None:
    """Register all virtual device services."""
    hass = MagicMock()
    storage = MagicMock()

    await async_register_virtual_device_services(hass, storage)

    registered_services = {
        call.args[1]
        for call in hass.services.async_register.call_args_list
    }

    assert "create_virtual_device" in registered_services
    assert "update_virtual_device" in registered_services
    assert "delete_virtual_device" in registered_services


@pytest.mark.asyncio
async def test_create_virtual_device_service_calls_manager() -> None:
    """Create service delegates to the virtual device manager."""
    hass = MagicMock()
    hass.data = {}

    # The integration storage will later live here.
    storage = MagicMock()

    with patch(
        "custom_components.virtual_device.virtual_device_services"
        ".async_create_virtual_device",
        new_callable=AsyncMock,
    ) as manager_mock:
        await async_register_virtual_device_services(hass, storage)

        service_call = MagicMock()
        service_call.data = {
            "label_ref": "label-id-energie",
            "name": "Haus Energie",
        }

        # Get the registered handler.
        register_call = next(
            call
            for call in hass.services.async_register.call_args_list
            if call.args[1] == "create_virtual_device"
        )
        handler = register_call.args[2]


        await handler(service_call)

    manager_mock.assert_awaited_once_with(
        hass=hass,
        storage=storage,
        label_ref="label-id-energie",
        name="Haus Energie",
    )


@pytest.mark.asyncio
async def test_create_virtual_device_service_allows_missing_name() -> None:
    """Create service allows the device name to be omitted."""
    hass = MagicMock()
    hass.data = {}

    storage = MagicMock()

    with patch(
        "custom_components.virtual_device.virtual_device_services"
        ".async_create_virtual_device",
        new_callable=AsyncMock,
    ) as manager_mock:
        await async_register_virtual_device_services(hass, storage)

        service_call = MagicMock()
        service_call.data = {
            "label_ref": "label-id-energie",
        }

        register_call = next(
            call
            for call in hass.services.async_register.call_args_list
            if call.args[1] == "create_virtual_device"
        )
        handler = register_call.args[2]

        await handler(service_call)

    manager_mock.assert_awaited_once_with(
        hass=hass,
        storage=storage,
        label_ref="label-id-energie",
        name=None,
    )


@pytest.mark.asyncio
async def test_update_virtual_device_service_calls_manager() -> None:
    """Update service delegates to the virtual device manager."""
    hass = MagicMock()
    hass.data = {}

    storage = MagicMock()

    with patch(
        "custom_components.virtual_device.virtual_device_services"
        ".async_update_virtual_device",
        new_callable=AsyncMock,
    ) as manager_mock:
        await async_register_virtual_device_services(hass, storage)

        service_call = MagicMock()
        service_call.data = {
            "device_id": "device-1",
            "name": "Haus Gesamtenergie",
        }

        register_call = next(
            call
            for call in hass.services.async_register.call_args_list
            if call.args[1] == "update_virtual_device"
        )
        handler = register_call.args[2]

        await handler(service_call)

    manager_mock.assert_awaited_once_with(
        hass=hass,
        storage=storage,
        device_id="device-1",
        name="Haus Gesamtenergie",
        label_ref=None,
    )


@pytest.mark.asyncio
async def test_update_virtual_device_service_allows_missing_name() -> None:
    """Update service allows the name to be omitted."""
    hass = MagicMock()
    hass.data = {}

    storage = MagicMock()

    with patch(
        "custom_components.virtual_device.virtual_device_services"
        ".async_update_virtual_device",
        new_callable=AsyncMock,
    ) as manager_mock:
        await async_register_virtual_device_services(hass, storage)

        service_call = MagicMock()
        service_call.data = {
            "device_id": "device-1",
        }

        register_call = next(
            call
            for call in hass.services.async_register.call_args_list
            if call.args[1] == "update_virtual_device"
        )
        handler = register_call.args[2]

        await handler(service_call)

    manager_mock.assert_awaited_once_with(
        hass=hass,
        storage=storage,
        device_id="device-1",
        name=None,
        label_ref=None,
    )


@pytest.mark.asyncio
async def test_delete_virtual_device_service_calls_manager() -> None:
    """Delete service delegates to the virtual device manager."""
    hass = MagicMock()
    hass.data = {}

    storage = MagicMock()

    with patch(
        "custom_components.virtual_device.virtual_device_services"
        ".async_delete_virtual_device",
        new_callable=AsyncMock,
    ) as manager_mock:
        await async_register_virtual_device_services(hass, storage)

        service_call = MagicMock()
        service_call.data = {
            "device_id": "device-1",
        }

        register_call = next(
            call
            for call in hass.services.async_register.call_args_list
            if call.args[1] == "delete_virtual_device"
        )
        handler = register_call.args[2]

        await handler(service_call)

    manager_mock.assert_awaited_once_with(
        hass=hass,
        storage=storage,
        device_id="device-1",
    )


@pytest.mark.asyncio
async def test_create_virtual_device_service_requires_label_ref() -> None:
    """Create service requires a label reference."""
    hass = MagicMock()
    hass.data = {}

    storage = MagicMock()

    with patch(
        "custom_components.virtual_device.virtual_device_services"
        ".async_create_virtual_device",
        new_callable=AsyncMock,
    ) as manager_mock:
        await async_register_virtual_device_services(hass, storage)

        service_call = MagicMock()
        service_call.data = {
            "name": "Haus Energie",
        }

        register_call = next(
            call
            for call in hass.services.async_register.call_args_list
            if call.args[1] == "create_virtual_device"
        )
        handler = register_call.args[2]

        with pytest.raises(ValueError):
            await handler(service_call)

        manager_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_virtual_device_service_requires_device_id() -> None:
    """Update service requires a device ID."""
    hass = MagicMock()
    hass.data = {}

    storage = MagicMock()

    with patch(
        "custom_components.virtual_device.virtual_device_services"
        ".async_update_virtual_device",
        new_callable=AsyncMock,
    ) as manager_mock:
        await async_register_virtual_device_services(hass, storage)

        service_call = MagicMock()
        service_call.data = {
            "name": "Haus Energie",
        }

        register_call = next(
            call
            for call in hass.services.async_register.call_args_list
            if call.args[1] == "update_virtual_device"
        )
        handler = register_call.args[2]

        with pytest.raises(ValueError):
            await handler(service_call)

        manager_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_virtual_device_service_requires_device_id() -> None:
    """Delete service requires a device ID."""
    hass = MagicMock()
    hass.data = {}

    storage = MagicMock()

    with patch(
        "custom_components.virtual_device.virtual_device_services"
        ".async_delete_virtual_device",
        new_callable=AsyncMock,
    ) as manager_mock:
        await async_register_virtual_device_services(hass, storage)

        service_call = MagicMock()
        service_call.data = {}

        register_call = next(
            call
            for call in hass.services.async_register.call_args_list
            if call.args[1] == "delete_virtual_device"
        )
        handler = register_call.args[2]

        with pytest.raises(ValueError):
            await handler(service_call)

        manager_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_virtual_device_service_rejects_empty_label_ref() -> None:
    """Create service rejects an empty label reference."""
    hass = MagicMock()
    hass.data = {}

    storage = MagicMock()

    with patch(
        "custom_components.virtual_device.virtual_device_services"
        ".async_create_virtual_device",
        new_callable=AsyncMock,
    ) as manager_mock:
        await async_register_virtual_device_services(hass, storage)

        service_call = MagicMock()
        service_call.data = {
            "label_ref": "",
        }

        register_call = next(
            call
            for call in hass.services.async_register.call_args_list
            if call.args[1] == "create_virtual_device"
        )
        handler = register_call.args[2]

        with pytest.raises(ValueError):
            await handler(service_call)

        manager_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_virtual_device_service_rejects_empty_device_id() -> None:
    """Update service rejects an empty device ID."""
    hass = MagicMock()
    hass.data = {}

    storage = MagicMock()

    with patch(
        "custom_components.virtual_device.virtual_device_services"
        ".async_update_virtual_device",
        new_callable=AsyncMock,
    ) as manager_mock:
        await async_register_virtual_device_services(hass, storage)

        service_call = MagicMock()
        service_call.data = {
            "device_id": "",
        }

        register_call = next(
            call
            for call in hass.services.async_register.call_args_list
            if call.args[1] == "update_virtual_device"
        )
        handler = register_call.args[2]

        with pytest.raises(ValueError):
            await handler(service_call)

        manager_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_virtual_device_service_rejects_empty_device_id() -> None:
    """Delete service rejects an empty device ID."""
    hass = MagicMock()
    hass.data = {}

    storage = MagicMock()

    with patch(
        "custom_components.virtual_device.virtual_device_services"
        ".async_delete_virtual_device",
        new_callable=AsyncMock,
    ) as manager_mock:
        await async_register_virtual_device_services(hass, storage)

        service_call = MagicMock()
        service_call.data = {
            "device_id": "",
        }

        register_call = next(
            call
            for call in hass.services.async_register.call_args_list
            if call.args[1] == "delete_virtual_device"
        )
        handler = register_call.args[2]

        with pytest.raises(ValueError):
            await handler(service_call)

        manager_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_virtual_device_services_have_expected_schemas() -> None:
    """Register virtual device services with the expected schemas."""
    hass = MagicMock()
    storage = MagicMock()
    hass.data = {}

    await async_register_virtual_device_services(hass, storage)

    registrations = {
        call.args[1]: call
        for call in hass.services.async_register.call_args_list
    }

    create_call = registrations["create_virtual_device"]
    update_call = registrations["update_virtual_device"]
    delete_call = registrations["delete_virtual_device"]

    assert create_call.kwargs["schema"] is not None
    assert update_call.kwargs["schema"] is not None
    assert delete_call.kwargs["schema"] is not None


@pytest.mark.asyncio
async def test_create_virtual_device_schema_requires_label_ref() -> None:
    """Create service schema requires label_ref."""
    hass = MagicMock()
    storage = MagicMock()
    hass.data = {}

    await async_register_virtual_device_services(hass, storage)

    register_call = next(
        call
        for call in hass.services.async_register.call_args_list
        if call.args[1] == "create_virtual_device"
    )

    schema = register_call.kwargs["schema"]

    with pytest.raises(vol.Invalid):
        schema({})

    assert schema({"label_ref": "label-id-energie"}) == {
        "label_ref": "label-id-energie",
    }


@pytest.mark.asyncio
async def test_update_virtual_device_schema_requires_device_id() -> None:
    """Update service schema requires device_id."""
    hass = MagicMock()
    storage = MagicMock()
    hass.data = {}

    await async_register_virtual_device_services(hass, storage)

    register_call = next(
        call
        for call in hass.services.async_register.call_args_list
        if call.args[1] == "update_virtual_device"
    )

    schema = register_call.kwargs["schema"]

    with pytest.raises(vol.Invalid):
        schema({})

    assert schema({"device_id": "virtual_energie"}) == {
        "device_id": "virtual_energie",
    }


@pytest.mark.asyncio
async def test_delete_virtual_device_schema_requires_device_id() -> None:
    """Delete service schema requires device_id."""
    hass = MagicMock()
    storage = MagicMock()
    hass.data = {}

    await async_register_virtual_device_services(hass, storage)

    register_call = next(
        call
        for call in hass.services.async_register.call_args_list
        if call.args[1] == "delete_virtual_device"
    )

    schema = register_call.kwargs["schema"]

    with pytest.raises(vol.Invalid):
        schema({})


@pytest.mark.asyncio
async def test_create_virtual_device_schema_accepts_optional_name() -> None:
    """Create service schema accepts an optional name."""
    hass = MagicMock()
    storage = MagicMock()
    hass.data = {}

    await async_register_virtual_device_services(hass, storage)

    register_call = next(
        call
        for call in hass.services.async_register.call_args_list
        if call.args[1] == "create_virtual_device"
    )

    schema = register_call.kwargs["schema"]

    assert schema(
        {
            "label_ref": "label-id-energie",
            "name": "Haus Energie",
        }
    ) == {
        "label_ref": "label-id-energie",
        "name": "Haus Energie",
    }


@pytest.mark.asyncio
async def test_update_virtual_device_schema_accepts_optional_name() -> None:
    """Update service schema accepts an optional name."""
    hass = MagicMock()
    storage = MagicMock()
    hass.data = {}

    await async_register_virtual_device_services(hass, storage)

    register_call = next(
        call
        for call in hass.services.async_register.call_args_list
        if call.args[1] == "update_virtual_device"
    )

    schema = register_call.kwargs["schema"]

    assert schema(
        {
            "device_id": "virtual_energie",
            "name": "Haus Energie",
        }
    ) == {
        "device_id": "virtual_energie",
        "name": "Haus Energie",
    }


@pytest.mark.asyncio
async def test_update_virtual_device_service_passes_label_ref() -> None:
    """Update service passes label_ref to the virtual device manager."""
    hass = MagicMock()
    hass.data = {}

    storage = MagicMock()

    with patch(
        "custom_components.virtual_device.virtual_device_services"
        ".async_update_virtual_device",
        new_callable=AsyncMock,
    ) as manager_mock:
        await async_register_virtual_device_services(hass, storage)

        service_call = MagicMock()
        service_call.data = {
            "device_id": "device-1",
            "label_ref": "label-id-gesamt",
        }

        register_call = next(
            call
            for call in hass.services.async_register.call_args_list
            if call.args[1] == "update_virtual_device"
        )
        handler = register_call.args[2]

        await handler(service_call)

    manager_mock.assert_awaited_once_with(
        hass=hass,
        storage=storage,
        device_id="device-1",
        label_ref="label-id-gesamt",
        name=None,
    )