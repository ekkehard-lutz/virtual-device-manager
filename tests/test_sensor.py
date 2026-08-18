"""Tests for Virtual Device Manager virtual sensors."""

from unittest.mock import MagicMock

import pytest
from homeassistant.const import (
    STATE_UNAVAILABLE,
)
from homeassistant.core import State

from custom_components.virtual_device.aggregator import SourceValue
from custom_components.virtual_device.const import DOMAIN
from custom_components.virtual_device.models import (
    VirtualDevice,
    VirtualEntity,
)
from custom_components.virtual_device.sensor import (
    VirtualDeviceSensor,
    VirtualSensorManager,
    async_setup_entry,
    async_unload_entry,
    handle_state_changed,
    source_value_from_state,
    update_sensors_for_source_change,
)
from custom_components.virtual_device.source_manager import SourceManager


def _create_sensor() -> VirtualDeviceSensor:
    """Create a test virtual sensor."""
    device = VirtualDevice(
        id="virtual_beleuchtung",
        name="Energie",
        label_ref="label-id-energie",
        entities=[
            VirtualEntity(
                id="virtual_beleuchtung_power",
                device_class="power",
                aggregation="sum",
                unit="kW",
            ),
        ],
    )

    return VirtualDeviceSensor(
        device,
        device.entities[0],
    )


def test_sensor_name() -> None:
    """Test the sensor name."""
    sensor = _create_sensor()

    assert sensor.name == "power"


def test_sensor_device_class() -> None:
    """Test the sensor device class."""
    sensor = _create_sensor()

    assert sensor.device_class == "power"


def test_sensor_unit() -> None:
    """Test the sensor unit."""
    sensor = _create_sensor()

    assert sensor.native_unit_of_measurement == "kW"


def test_sensor_initial_value() -> None:
    """Test the initial sensor value."""
    sensor = _create_sensor()

    assert sensor.native_value is None


def test_sensor_manager_add_entity() -> None:
    """Test adding a virtual sensor at runtime."""
    sensor = _create_sensor()
    add_entities = MagicMock()

    manager = VirtualSensorManager()
    manager.initialize(add_entities)

    manager.add_entity(
        device=sensor._device,
        entity=sensor._virtual_entity,
        values=[
            SourceValue(
                "sensor.power",
                500,
                "W",
            ),
            SourceValue(
                "sensor.power_2",
                1.5,
                "kW",
            ),
        ],
    )

    add_entities.assert_called_once()

    added_sensor = add_entities.call_args.args[0][0]

    assert isinstance(
        added_sensor,
        VirtualDeviceSensor,
    )

    assert added_sensor.unique_id == (
        "virtual_device_virtual_beleuchtung_power"
    )

    assert added_sensor.native_value == 2.0

    assert manager.sensors[
        "virtual_beleuchtung_power"
    ] is added_sensor


def test_sensor_unique_id() -> None:
    """Test the sensor unique ID."""
    sensor = _create_sensor()

    assert sensor.unique_id == (
        "virtual_device_virtual_beleuchtung_power"
    )


def test_sensor_update_value_sum() -> None:
    """Test sensor value calculation using sum."""
    sensor = _create_sensor()

    sensor.hass = MagicMock()
    sensor.async_write_ha_state = MagicMock()

    sensor.update_value(
        [
            SourceValue("sensor.power_1", 500, "W"),
            SourceValue("sensor.power_2", 1.5, "kW"),
        ]
    )

    assert sensor.native_value == 2.0


def test_sensor_update_value_average() -> None:
    """Test sensor value calculation using average."""
    device = VirtualDevice(
        id="device-1",
        name="Energie",
        label_ref="label-id-energie",
        entities=[
            VirtualEntity(
                id="power",
                device_class="power",
                aggregation="avg",
                unit="kW",
            ),
        ],
    )

    sensor = VirtualDeviceSensor(
        device,
        device.entities[0],
    )

    sensor.hass = MagicMock()
    sensor.async_write_ha_state = MagicMock()

    sensor.update_value(
        [
            SourceValue("sensor.power_1", 500, "W"),
            SourceValue("sensor.power_2", 1.5, "kW"),
        ]
    )

    assert sensor.native_value == 1.0


def test_sensor_update_value_min() -> None:
    """Test sensor value calculation using minimum."""
    device = VirtualDevice(
        id="device-1",
        name="Energie",
        label_ref="label-id-energie",
        entities=[
            VirtualEntity(
                id="power",
                device_class="power",
                aggregation="min",
                unit="kW",
            ),
        ],
    )

    sensor = VirtualDeviceSensor(
        device,
        device.entities[0],
    )

    sensor.hass = MagicMock()
    sensor.async_write_ha_state = MagicMock()

    sensor.update_value(
        [
            SourceValue("sensor.power_1", 500, "W"),
            SourceValue("sensor.power_2", 1.5, "kW"),
        ]
    )

    assert sensor.native_value == 0.5


def test_sensor_update_value_max() -> None:
    """Test sensor value calculation using maximum."""
    device = VirtualDevice(
        id="device-1",
        name="Energie",
        label_ref="label-id-energie",
        entities=[
            VirtualEntity(
                id="power",
                device_class="power",
                aggregation="max",
                unit="kW",
            ),
        ],
    )

    sensor = VirtualDeviceSensor(
        device,
        device.entities[0],
    )

    sensor.hass = MagicMock()
    sensor.async_write_ha_state = MagicMock()

    sensor.update_value(
        [
            SourceValue("sensor.power_1", 500, "W"),
            SourceValue("sensor.power_2", 1.5, "kW"),
        ]
    )

    assert sensor.native_value == 1.5


def test_sensor_update_value_empty() -> None:
    """Test sensor value with no source values."""
    sensor = _create_sensor()

    sensor.hass = MagicMock()
    sensor.async_write_ha_state = MagicMock()

    sensor.update_value([])

    assert sensor.native_value is None


@pytest.mark.asyncio
async def test_async_setup_entry_creates_virtual_sensors(
    monkeypatch,
) -> None:
    """Test creation of virtual sensors from stored devices."""
    hass = MagicMock()
    entry = MagicMock()

    device = VirtualDevice(
        id="device-1",
        name="Energie",
        label_ref="label-id-energie",
        entities=[
            VirtualEntity(
                id="power",
                device_class="power",
                aggregation="sum",
                unit="kW",
            ),
            VirtualEntity(
                id="energy",
                device_class="energy",
                aggregation="sum",
                unit="kWh",
            ),
        ],
    )

    storage = MagicMock()
    storage.get_virtual_devices.return_value = [device]

    sensor_manager = VirtualSensorManager()

    hass.data = {
        DOMAIN: {
            entry.entry_id: {
                "storage": storage,
                "source_manager": SourceManager(),
                "sensor_manager": sensor_manager,
            },
        },
    }

    add_entities = MagicMock()

    from custom_components.virtual_device import sensor

    await sensor.async_setup_entry(
        hass,
        entry,
        add_entities,
    )

    add_entities.assert_called_once()

    entities = add_entities.call_args.args[0]

    assert len(entities) == 2
    assert all(
        isinstance(entity, VirtualDeviceSensor)
        for entity in entities
    )

    assert entities[0].unique_id == "virtual_device_power"
    assert entities[1].unique_id == "virtual_device_energy"


def test_sensor_device_info() -> None:
    """Test virtual device information."""
    sensor = _create_sensor()

    device_info = sensor.device_info

    assert device_info is not None
    assert device_info["identifiers"] == {
        ("virtual_device", "virtual_beleuchtung")
    }
    assert device_info["name"] == "Energie"


def test_sensors_share_virtual_device() -> None:
    """Test that virtual entities share one HA device."""
    device = VirtualDevice(
        id="device-1",
        name="Energie",
        label_ref="label-id-energie",
        entities=[
            VirtualEntity(
                id="power",
                device_class="power",
                aggregation="sum",
                unit="kW",
            ),
            VirtualEntity(
                id="energy",
                device_class="energy",
                aggregation="sum",
                unit="kWh",
            ),
        ],
    )

    power_sensor = VirtualDeviceSensor(
        device,
        device.entities[0],
    )
    energy_sensor = VirtualDeviceSensor(
        device,
        device.entities[1],
    )

    assert power_sensor.device_info["identifiers"] == (
        energy_sensor.device_info["identifiers"]
    )


def test_different_virtual_devices_have_different_ids() -> None:
    """Test that different virtual devices are distinct."""
    device_1 = VirtualDevice(
        id="device-1",
        name="Energie",
        label_ref="label-id-energie",
        entities=[
            VirtualEntity(
                id="power",
                device_class="power",
                aggregation="sum",
                unit="kW",
            ),
        ],
    )

    device_2 = VirtualDevice(
        id="device-2",
        name="Energie 2",
        label_ref="label-id-energie",
        entities=[
            VirtualEntity(
                id="power",
                device_class="power",
                aggregation="sum",
                unit="kW",
            ),
        ],
    )

    sensor_1 = VirtualDeviceSensor(
        device_1,
        device_1.entities[0],
    )
    sensor_2 = VirtualDeviceSensor(
        device_2,
        device_2.entities[0],
    )

    assert sensor_1.device_info["identifiers"] != (
        sensor_2.device_info["identifiers"]
    )



def test_sensor_update_value_writes_state() -> None:
    """Test that updating the value writes the HA state."""
    sensor = _create_sensor()

    sensor.async_write_ha_state = MagicMock()

    sensor.update_value(
        [
            SourceValue("sensor.power_1", 500, "W"),
            SourceValue("sensor.power_2", 1.5, "kW"),
        ]
    )

    assert sensor.native_value == 2.0
    sensor.async_write_ha_state.assert_called_once()


def test_update_sensors_for_source_change() -> None:
    """Update only virtual sensors affected by a source change."""
    device = VirtualDevice(
        id="device-1",
        name="Energie",
        label_ref="label-id-energie",
        entities=[
            VirtualEntity(
                id="power",
                device_class="power",
                aggregation="sum",
                unit="kW",
            ),
            VirtualEntity(
                id="energy",
                device_class="energy",
                aggregation="sum",
                unit="kWh",
            ),
        ],
    )

    power_sensor = VirtualDeviceSensor(
        device,
        device.entities[0],
    )
    energy_sensor = VirtualDeviceSensor(
        device,
        device.entities[1],
    )

    power_sensor.update_value = MagicMock()
    energy_sensor.update_value = MagicMock()

    source_manager = MagicMock()

    source_manager.handle_source_change.return_value = [
        "power",
    ]

    source_manager.get_source_values.return_value = [
        SourceValue(
            "sensor.power",
            1250,
            "W",
        ),
    ]

    update_sensors_for_source_change(
        source_manager,
        {
            "power": power_sensor,
            "energy": energy_sensor,
        },
        "sensor.power",
    )

    power_sensor.update_value.assert_called_once_with(
        [
            SourceValue(
                "sensor.power",
                1250,
                "W",
            ),
        ]
    )

    energy_sensor.update_value.assert_not_called()


def test_update_sensors_for_unknown_source() -> None:
    """Do not update sensors for an unknown source."""
    sensor = _create_sensor()
    sensor.update_value = MagicMock()

    source_manager = MagicMock()
    source_manager.handle_source_change.return_value = []

    update_sensors_for_source_change(
        source_manager,
        {"power": sensor},
        "sensor.unknown",
    )

    sensor.update_value.assert_not_called()


@pytest.mark.asyncio
async def test_handle_state_changed_unknown_source() -> None:
    """Ignore state changes from unknown source entities."""
    source_manager = MagicMock()
    source_manager.handle_source_change.return_value = []

    sensors = {
        "power": _create_sensor(),
    }

    event = MagicMock()
    event.data = {
        "entity_id": "sensor.unknown",
        "old_state": None,
        "new_state": MagicMock(),
    }

    await handle_state_changed(
        source_manager,
        sensors,
        event,
    )

    source_manager.handle_source_change.assert_called_once_with(
        "sensor.unknown",
    )


@pytest.mark.asyncio
async def test_handle_state_changed_without_new_state() -> None:
    """Ignore state changes without a new state."""
    source_manager = MagicMock()
    sensors = {
        "power": _create_sensor(),
    }

    event = MagicMock()
    event.data = {
        "entity_id": "sensor.power",
        "old_state": MagicMock(),
        "new_state": None,
    }

    await handle_state_changed(
        source_manager,
        sensors,
        event,
    )

    source_manager.handle_source_change.assert_not_called()


@pytest.mark.asyncio
async def test_handle_state_changed_updates_affected_sensor() -> None:
    """Update affected virtual sensors after a state change."""
    sensor = _create_sensor()
    sensor.update_value = MagicMock()

    source_manager = MagicMock()
    source_manager.handle_source_change.return_value = [
        "power",
    ]

    event = MagicMock()
    event.data = {
        "entity_id": "sensor.power",
        "old_state": MagicMock(),
        "new_state": MagicMock(),
    }

    await handle_state_changed(
        source_manager,
        {"power": sensor},
        event,
    )

    source_manager.handle_source_change.assert_called_once_with(
        "sensor.power",
    )

    sensor.update_value.assert_called_once()


def test_source_value_from_state() -> None:
    """Convert a numeric HA state into a SourceValue."""
    state = State(
        "sensor.power",
        "1250",
        {
            "unit_of_measurement": "W",
        },
    )

    result = source_value_from_state(
        "sensor.power",
        state,
    )

    assert result is not None
    assert result.entity_id == "sensor.power"
    assert result.value == 1250.0
    assert result.unit == "W"


def test_source_value_from_invalid_state() -> None:
    """Ignore non-numeric states."""
    state = State(
        "sensor.power",
        "unknown",
        {
            "unit_of_measurement": "W",
        },
    )

    assert (
        source_value_from_state(
            "sensor.power",
            state,
        )
        is None
    )


def test_source_value_from_unavailable_state() -> None:
    """Ignore unavailable states."""
    state = State(
        "sensor.power",
        STATE_UNAVAILABLE,
        {
            "unit_of_measurement": "W",
        },
    )

    assert (
        source_value_from_state(
            "sensor.power",
            state,
        )
        is None
    )


@pytest.mark.asyncio
async def test_handle_state_changed_updates_source_cache() -> None:
    """Update the source cache from a Home Assistant state change."""
    sensor = _create_sensor()
    sensor.update_value = MagicMock()

    source_manager = MagicMock()
    source_manager.handle_source_change.return_value = [
        "power",
    ]
    source_manager.get_source_values.return_value = [
        SourceValue(
            "sensor.power",
            1250.0,
            "W",
        ),
    ]

    event = MagicMock()
    event.data = {
        "entity_id": "sensor.power",
        "old_state": State(
            "sensor.power",
            "1000",
            {"unit_of_measurement": "W"},
        ),
        "new_state": State(
            "sensor.power",
            "1250",
            {
                "device_class": "power",
                "unit_of_measurement": "W",
            },
        ),
    }

    await handle_state_changed(
        source_manager,
        {"power": sensor},
        event,
    )

    source_manager.update_source_value.assert_called_once_with(
        SourceValue(
            "sensor.power",
            1250.0,
            "W",
        )
    )

    source_manager.get_source_values.assert_called_once_with(
        "power",
    )

    sensor.update_value.assert_called_once_with(
        [
            SourceValue(
                "sensor.power",
                1250.0,
                "W",
            ),
        ]
    )


@pytest.mark.asyncio
async def test_async_setup_entry_uses_source_manager_and_creates_listener(
    monkeypatch,
) -> None:
    """Create the source manager and register the state listener."""
    hass = MagicMock()
    entry = MagicMock()

    device = VirtualDevice(
        id="device-1",
        name="Energie",
        label_ref="label-id-energie",
        entities=[
            VirtualEntity(
                id="power",
                device_class="power",
                aggregation="sum",
                unit="kW",
            ),
        ],
    )

    storage = MagicMock()
    storage.get_virtual_devices.return_value = [device]

    sensor_manager = VirtualSensorManager()

    hass.data = {
        DOMAIN: {
            entry.entry_id: {
                "storage": storage,
                "source_manager": SourceManager(),
                "sensor_manager": sensor_manager,
            },
        },
    }

    add_entities = MagicMock()

    async_listen = MagicMock(return_value=MagicMock())
    monkeypatch.setattr(
        hass.bus,
        "async_listen",
        async_listen,
    )

    rebuild = MagicMock()
    monkeypatch.setattr(
        SourceManager,
        "rebuild_virtual_device",
        rebuild,
    )

    await async_setup_entry(
        hass,
        entry,
        add_entities,
    )

    entry_data = hass.data[DOMAIN][entry.entry_id]

    assert isinstance(
        entry_data["source_manager"],
        SourceManager,
    )

    rebuild.assert_called_once_with(
        hass,
        device,
    )

    async_listen.assert_called_once() 


@pytest.mark.asyncio
async def test_async_unload_entry_removes_state_listener() -> None:
    """Remove the state listener when the config entry is unloaded."""
    hass = MagicMock()
    entry = MagicMock()

    unsubscribe = MagicMock()

    hass.data = {
        DOMAIN: {
            entry.entry_id: {
                "sensor_unsubscribe": unsubscribe,
            },
        },
    }

    await async_unload_entry(hass, entry)

    unsubscribe.assert_called_once()
    assert entry.entry_id not in hass.data[DOMAIN]


@pytest.mark.asyncio
async def test_state_changed_aggregates_all_cached_sources() -> None:
    """Aggregate all cached source values after one source changes."""
    device = VirtualDevice(
        id="device-1",
        name="Energie",
        label_ref="label-id-energie",
        entities=[
            VirtualEntity(
                id="power",
                device_class="power",
                aggregation="sum",
                unit="W",
            ),
        ],
    )

    sensor = VirtualDeviceSensor(
        device,
        device.entities[0],
    )

    sensor.hass = MagicMock()
    sensor.async_write_ha_state = MagicMock()

    source_manager = SourceManager()

    source_manager.add_source(
        "power",
        "sensor.power_1",
    )
    source_manager.add_source(
        "power",
        "sensor.power_2",
    )

    source_manager.update_source_value(
        SourceValue(
            entity_id="sensor.power_1",
            value=100.0,
            unit="W",
        )
    )

    source_manager.update_source_value(
        SourceValue(
            entity_id="sensor.power_2",
            value=50.0,
            unit="W",
        )
    )

    sensors = {
        "power": sensor,
    }

    # power_1 changes from 100 W to 120 W.
    state = State(
        "sensor.power_1",
        "120",
        {
            "device_class": "power",
            "unit_of_measurement": "W",
        },
    )

    event = MagicMock()
    event.data = {
        "entity_id": "sensor.power_1",
        "new_state": state,
    }

    await handle_state_changed(
        source_manager,
        sensors,
        event,
    )

    assert sensor.native_value == 170.0
