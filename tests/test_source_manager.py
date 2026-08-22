"""Tests for the Virtual Device Manager source manager."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.virtual_device.aggregator import SourceValue
from custom_components.virtual_device.models import (
    VirtualDevice,
    VirtualEntity,
)
from custom_components.virtual_device.source_manager import SourceManager


def test_empty_source_manager() -> None:
    """Test an empty source manager."""
    manager = SourceManager()

    assert manager.get_sources("virtual-entity-1") == []
    assert manager.get_virtual_entities("sensor.test") == []


def test_add_source() -> None:
    """Test adding a source relationship."""
    manager = SourceManager()

    manager.add_source(
        "virtual-entity-1",
        "sensor.power",
    )

    assert manager.get_sources("virtual-entity-1") == [
        "sensor.power",
    ]

    assert manager.get_virtual_entities("sensor.power") == [
        "virtual-entity-1",
    ]


def test_add_multiple_sources() -> None:
    """Test multiple sources for one virtual entity."""
    manager = SourceManager()

    manager.add_source(
        "virtual-entity-1",
        "sensor.power_1",
    )
    manager.add_source(
        "virtual-entity-1",
        "sensor.power_2",
    )

    assert manager.get_sources("virtual-entity-1") == [
        "sensor.power_1",
        "sensor.power_2",
    ]


def test_source_can_belong_to_multiple_virtual_entities() -> None:
    """Test one source used by multiple virtual entities."""
    manager = SourceManager()

    manager.add_source(
        "virtual-entity-1",
        "sensor.power",
    )
    manager.add_source(
        "virtual-entity-2",
        "sensor.power",
    )

    assert manager.get_virtual_entities("sensor.power") == [
        "virtual-entity-1",
        "virtual-entity-2",
    ]


def test_duplicate_source_is_ignored() -> None:
    """Test that duplicate relationships are ignored."""
    manager = SourceManager()

    manager.add_source(
        "virtual-entity-1",
        "sensor.power",
    )
    manager.add_source(
        "virtual-entity-1",
        "sensor.power",
    )

    assert manager.get_sources("virtual-entity-1") == [
        "sensor.power",
    ]

    assert manager.get_virtual_entities("sensor.power") == [
        "virtual-entity-1",
    ]


def test_remove_source() -> None:
    """Test removing a source relationship."""
    manager = SourceManager()

    manager.add_source(
        "virtual-entity-1",
        "sensor.power",
    )

    manager.remove_source(
        "virtual-entity-1",
        "sensor.power",
    )

    assert manager.get_sources("virtual-entity-1") == []
    assert manager.get_virtual_entities("sensor.power") == []


def test_clear() -> None:
    """Test clearing all source relationships."""
    manager = SourceManager()

    manager.add_source(
        "virtual-entity-1",
        "sensor.power",
    )
    manager.add_source(
        "virtual-entity-2",
        "sensor.energy",
    )

    manager.clear()

    assert manager.get_sources("virtual-entity-1") == []
    assert manager.get_sources("virtual-entity-2") == []
    assert manager.get_virtual_entities("sensor.power") == []
    assert manager.get_virtual_entities("sensor.energy") == []


def test_rebuild_virtual_device(monkeypatch) -> None:
    """Test rebuilding sources for one virtual device."""
    hass = MagicMock()

    device = VirtualDevice(
        id="device-1",
        name="Energie",
        label_ref="label-id-energie",
        entities=[
            VirtualEntity(
                id="power",
                device_class="power",
                aggregation="sum",
            ),
        ],
    )

    from custom_components.virtual_device import source_manager

    monkeypatch.setattr(
        source_manager,
        "get_source_entities",
        lambda hass, label, device_class: [
            "sensor.power_1",
            "sensor.power_2",
        ],
    )

    manager = SourceManager()

    manager.rebuild_virtual_device(
        hass,
        device,
    )

    assert manager.get_sources("power") == [
        "sensor.power_1",
        "sensor.power_2",
    ]

    assert manager.get_virtual_entities("sensor.power_1") == [
        "power",
    ]

    assert manager.get_virtual_entities("sensor.power_2") == [
        "power",
    ]


def test_rebuild_virtual_device_multiple_entities(monkeypatch) -> None:
    """Test rebuilding multiple virtual entities."""
    hass = MagicMock()

    device = VirtualDevice(
        id="device-1",
        name="Energie",
        label_ref="label-id-energie",
        entities=[
            VirtualEntity(
                id="power",
                device_class="power",
                aggregation="sum",
            ),
            VirtualEntity(
                id="energy",
                device_class="energy",
                aggregation="sum",
            ),
        ],
    )

    def fake_get_source_entities(
        hass,
        label,
        device_class,
    ):
        if device_class == "power":
            return [
                "sensor.power_1",
                "sensor.power_2",
            ]

        if device_class == "energy":
            return [
                "sensor.energy_1",
            ]

        return []

    from custom_components.virtual_device import source_manager

    monkeypatch.setattr(
        source_manager,
        "get_source_entities",
        fake_get_source_entities,
    )

    manager = SourceManager()

    manager.rebuild_virtual_device(
        hass,
        device,
    )

    assert manager.get_sources("power") == [
        "sensor.power_1",
        "sensor.power_2",
    ]

    assert manager.get_sources("energy") == [
        "sensor.energy_1",
    ]

    assert manager.get_virtual_entities("sensor.power_1") == [
        "power",
    ]

    assert manager.get_virtual_entities("sensor.energy_1") == [
        "energy",
    ]


def test_rebuild_virtual_device_removes_old_sources(
    monkeypatch,
) -> None:
    """Test that rebuild removes obsolete sources."""
    hass = MagicMock()

    device = VirtualDevice(
        id="device-1",
        name="Energie",
        label_ref="label-id-energie",
        entities=[
            VirtualEntity(
                id="power",
                device_class="power",
                aggregation="sum",
            ),
        ],
    )

    from custom_components.virtual_device import source_manager

    monkeypatch.setattr(
        source_manager,
        "get_source_entities",
        lambda hass, label, device_class: [
            "sensor.power_1",
            "sensor.power_2",
        ],
    )

    manager = SourceManager()

    manager.rebuild_virtual_device(
        hass,
        device,
    )

    assert manager.get_sources("power") == [
        "sensor.power_1",
        "sensor.power_2",
    ]

    monkeypatch.setattr(
        source_manager,
        "get_source_entities",
        lambda hass, label, device_class: [
            "sensor.power_1",
        ],
    )

    manager.rebuild_virtual_device(
        hass,
        device,
    )

    assert manager.get_sources("power") == [
        "sensor.power_1",
    ]

    assert manager.get_virtual_entities("sensor.power_1") == [
        "power",
    ]

    assert manager.get_virtual_entities("sensor.power_2") == []


def test_get_affected_virtual_entities_unknown_source() -> None:
    """Return no virtual entities for an unknown source."""
    manager = SourceManager()

    assert manager.get_affected_virtual_entities("sensor.unknown") == []


def test_get_affected_virtual_entities_single() -> None:
    """Return the virtual entity using a source."""
    manager = SourceManager()

    manager.add_source(
        "virtual-entity-1",
        "sensor.power",
    )

    assert manager.get_affected_virtual_entities("sensor.power") == [
        "virtual-entity-1",
    ]


def test_get_affected_virtual_entities_multiple() -> None:
    """Return all virtual entities using a source."""
    manager = SourceManager()

    manager.add_source(
        "virtual-entity-1",
        "sensor.power",
    )
    manager.add_source(
        "virtual-entity-2",
        "sensor.power",
    )

    assert manager.get_affected_virtual_entities("sensor.power") == [
        "virtual-entity-1",
        "virtual-entity-2",
    ]


def test_get_affected_virtual_entities_ignores_other_sources() -> None:
    """Return only virtual entities affected by the changed source."""
    manager = SourceManager()

    manager.add_source(
        "virtual-entity-1",
        "sensor.power",
    )
    manager.add_source(
        "virtual-entity-2",
        "sensor.energy",
    )

    assert manager.get_affected_virtual_entities("sensor.power") == [
        "virtual-entity-1",
    ]


def test_handle_source_change() -> None:
    """Return affected virtual entities for a source change."""
    manager = SourceManager()

    manager.add_source(
        "virtual-entity-1",
        "sensor.power",
    )
    manager.add_source(
        "virtual-entity-2",
        "sensor.power",
    )
    manager.add_source(
        "virtual-entity-3",
        "sensor.energy",
    )

    assert manager.handle_source_change("sensor.power") == [
        "virtual-entity-1",
        "virtual-entity-2",
    ]


def test_handle_source_change_unknown() -> None:
    """Return no entities for an unknown source change."""
    manager = SourceManager()

    assert manager.handle_source_change("sensor.unknown") == []


def test_handle_source_change_uses_existing_index() -> None:
    """Use the existing reverse index for source changes."""
    manager = SourceManager()

    manager.add_source(
        "power",
        "sensor.power",
    )
    manager.add_source(
        "energy",
        "sensor.energy",
    )

    assert manager.handle_source_change(
        "sensor.power",
    ) == ["power"]


def test_handle_source_change_does_not_rebuild_sources() -> None:
    """Source changes use the existing reverse index."""
    manager = SourceManager()

    manager.add_source(
        "power",
        "sensor.power",
    )

    # The lookup must work solely from the in-memory index.
    assert manager.handle_source_change(
        "sensor.power",
    ) == ["power"]

    assert manager.get_sources("power") == [
        "sensor.power",
    ]


def test_source_value_cache() -> None:
    """Cache and return a source value."""
    manager = SourceManager()

    value = SourceValue(
        entity_id="sensor.power",
        value=100.0,
        unit="W",
    )

    manager.add_source(
        "virtual-entity-1",
        "sensor.power",
    )

    affected = manager.update_source_value(value)

    assert affected == ["virtual-entity-1"]
    assert manager.get_source_value("sensor.power") == value

    assert manager.get_source_values("virtual-entity-1") == [value]


def test_source_value_cache_updates_existing_value() -> None:
    """Update an existing cached source value."""
    manager = SourceManager()

    manager.add_source(
        "virtual-entity-1",
        "sensor.power",
    )

    manager.update_source_value(
        SourceValue(
            entity_id="sensor.power",
            value=88.0,
            unit="W",
        )
    )

    manager.update_source_value(
        SourceValue(
            entity_id="sensor.power",
            value=100.0,
            unit="W",
        )
    )

    values = manager.get_source_values("virtual-entity-1")

    assert len(values) == 1
    assert values[0].value == 100.0


def test_source_values_are_cached_independently() -> None:
    """Keep all source values for a virtual entity."""
    manager = SourceManager()

    manager.add_source(
        "virtual-entity-1",
        "sensor.power_1",
    )
    manager.add_source(
        "virtual-entity-1",
        "sensor.power_2",
    )
    manager.add_source(
        "virtual-entity-1",
        "sensor.power_3",
    )

    manager.update_source_value(
        SourceValue(
            entity_id="sensor.power_1",
            value=100.0,
            unit="W",
        )
    )
    manager.update_source_value(
        SourceValue(
            entity_id="sensor.power_2",
            value=50.0,
            unit="W",
        )
    )
    manager.update_source_value(
        SourceValue(
            entity_id="sensor.power_3",
            value=30.0,
            unit="W",
        )
    )

    values = manager.get_source_values("virtual-entity-1")

    assert values == [
        SourceValue(
            entity_id="sensor.power_1",
            value=100.0,
            unit="W",
        ),
        SourceValue(
            entity_id="sensor.power_2",
            value=50.0,
            unit="W",
        ),
        SourceValue(
            entity_id="sensor.power_3",
            value=30.0,
            unit="W",
        ),
    ]


def test_source_value_can_be_shared_by_multiple_virtual_entities() -> None:
    """Cache one source value for multiple virtual entities."""
    manager = SourceManager()

    manager.add_source(
        "virtual-power",
        "sensor.power",
    )
    manager.add_source(
        "virtual-energy",
        "sensor.power",
    )

    value = SourceValue(
        entity_id="sensor.power",
        value=100.0,
        unit="W",
    )

    manager.update_source_value(value)

    assert manager.get_source_values("virtual-power") == [value]

    assert manager.get_source_values("virtual-energy") == [value]


def test_remove_source_removes_unused_cached_value() -> None:
    """Remove a cached value when its source is no longer used."""
    manager = SourceManager()

    manager.add_source(
        "virtual-entity-1",
        "sensor.power",
    )

    manager.update_source_value(
        SourceValue(
            entity_id="sensor.power",
            value=100.0,
            unit="W",
        )
    )

    manager.remove_source(
        "virtual-entity-1",
        "sensor.power",
    )

    assert manager.get_source_value("sensor.power") is None


def test_remove_source_value_keeps_relationship() -> None:
    """Removing a value keeps the source relationship."""
    manager = SourceManager()

    manager.add_source(
        "virtual-entity-1",
        "sensor.power",
    )

    manager.update_source_value(
        SourceValue(
            entity_id="sensor.power",
            value=100.0,
            unit="W",
        )
    )

    affected = manager.remove_source_value("sensor.power")

    assert affected == ["virtual-entity-1"]
    assert manager.get_sources("virtual-entity-1") == ["sensor.power"]
    assert manager.get_source_values("virtual-entity-1") == []


@pytest.mark.asyncio
async def test_reconcile_rebuilds_source_value_cache() -> None:
    """Reconciliation rebuilds the cache from current HA states."""
    hass = MagicMock()

    state_1 = MagicMock()
    state_1.entity_id = "sensor.power_1"
    state_1.state = "100"
    state_1.attributes = {
        "device_class": "power",
        "unit_of_measurement": "W",
    }

    state_2 = MagicMock()
    state_2.entity_id = "sensor.power_2"
    state_2.state = "50"
    state_2.attributes = {
        "device_class": "power",
        "unit_of_measurement": "W",
    }

    hass.states.get.side_effect = {
        "sensor.power_1": state_1,
        "sensor.power_2": state_2,
    }.get

    manager = SourceManager()

    manager.add_source(
        "power",
        "sensor.power_1",
    )
    manager.add_source(
        "power",
        "sensor.power_2",
    )

    # Deliberately wrong cache.
    manager.update_source_value(
        SourceValue(
            entity_id="sensor.power_1",
            value=999.0,
            unit="W",
        )
    )

    manager.update_source_value(
        SourceValue(
            entity_id="sensor.power_2",
            value=999.0,
            unit="W",
        )
    )

    await manager.async_reconcile(hass)

    assert manager.get_source_values("power") == [
        SourceValue(
            entity_id="sensor.power_1",
            value=100.0,
            unit="W",
        ),
        SourceValue(
            entity_id="sensor.power_2",
            value=50.0,
            unit="W",
        ),
    ]


def test_reconciliation_interval_default() -> None:
    """Use the default reconciliation interval."""
    manager = SourceManager()

    assert manager.reconciliation_interval == 300


def test_reconciliation_interval_is_configurable() -> None:
    """Allow configuring the reconciliation interval."""
    manager = SourceManager(
        reconciliation_interval=120,
    )

    assert manager.reconciliation_interval == 120


def test_reconciliation_can_be_disabled() -> None:
    """Allow disabling periodic reconciliation."""
    manager = SourceManager(
        reconciliation_interval=0,
    )

    assert manager.reconciliation_interval == 0


@pytest.mark.asyncio
async def test_async_start_creates_reconciliation_task(
    monkeypatch,
) -> None:
    """Start the periodic reconciliation task."""
    hass = MagicMock()

    manager = SourceManager(
        reconciliation_interval=300,
    )

    reconcile_mock = AsyncMock()

    monkeypatch.setattr(
        manager,
        "async_reconcile",
        reconcile_mock,
    )

    await manager.async_start(hass)

    assert manager._reconciliation_task is not None

    await manager.async_stop()


@pytest.mark.asyncio
async def test_async_start_disabled_when_interval_is_zero() -> None:
    """Do not create a task when reconciliation is disabled."""
    hass = MagicMock()

    manager = SourceManager(
        reconciliation_interval=0,
    )

    await manager.async_start(hass)

    assert manager._reconciliation_task is None

    await manager.async_stop()


@pytest.mark.asyncio
async def test_async_stop_cancels_reconciliation_task() -> None:
    """Stop the periodic reconciliation task."""
    hass = MagicMock()

    manager = SourceManager(
        reconciliation_interval=300,
    )

    await manager.async_start(hass)

    assert manager._reconciliation_task is not None

    await manager.async_stop()

    assert manager._reconciliation_task is None


@pytest.mark.asyncio
async def test_reconciliation_task_runs_reconcile() -> None:
    """Run reconciliation periodically."""
    hass = MagicMock()

    manager = SourceManager(
        reconciliation_interval=0.01,
    )

    reconcile_mock = AsyncMock()
    manager.async_reconcile = reconcile_mock

    await manager.async_start(hass)

    try:
        await asyncio.sleep(0.03)
    finally:
        await manager.async_stop()

    assert reconcile_mock.await_count >= 1
    reconcile_mock.assert_awaited_with(hass)


@pytest.mark.asyncio
async def test_reconcile_discovers_new_source_entity(
    monkeypatch,
) -> None:
    """Reconciliation discovers a newly matching source entity."""
    hass = MagicMock()

    device = VirtualDevice(
        id="device-1",
        name="Energie",
        label_ref="label-id-energie",
        entities=[
            VirtualEntity(
                id="power",
                device_class="power",
                aggregation="sum",
            ),
        ],
    )

    manager = SourceManager()

    monkeypatch.setattr(
        "custom_components.virtual_device.source_manager.get_source_entities",
        lambda hass, label, device_class: [
            "sensor.power_1",
        ],
    )

    manager.rebuild_virtual_device(
        hass,
        device,
    )

    assert manager.get_sources("power") == [
        "sensor.power_1",
    ]

    monkeypatch.setattr(
        "custom_components.virtual_device.source_manager.get_source_entities",
        lambda hass, label, device_class: [
            "sensor.power_1",
            "sensor.power_2",
        ],
    )

    state_1 = MagicMock()
    state_1.state = "100"
    state_1.attributes = {
        "device_class": "power",
        "unit_of_measurement": "W",
    }

    state_2 = MagicMock()
    state_2.state = "50"
    state_2.attributes = {
        "device_class": "power",
        "unit_of_measurement": "W",
    }

    hass.states.get.side_effect = {
        "sensor.power_1": state_1,
        "sensor.power_2": state_2,
    }.get

    await manager.async_reconcile(hass)

    assert manager.get_sources("power") == [
        "sensor.power_1",
        "sensor.power_2",
    ]

    assert manager.get_source_values("power") == [
        SourceValue(
            entity_id="sensor.power_1",
            value=100.0,
            unit="W",
        ),
        SourceValue(
            entity_id="sensor.power_2",
            value=50.0,
            unit="W",
        ),
    ]


@pytest.mark.asyncio
async def test_reconcile_removes_no_longer_matching_source_entity(
    monkeypatch,
) -> None:
    """Reconciliation removes a source that no longer matches."""
    hass = MagicMock()

    device = VirtualDevice(
        id="device-1",
        name="Energie",
        label_ref="label-id-energie",
        entities=[
            VirtualEntity(
                id="power",
                device_class="power",
                aggregation="sum",
            ),
        ],
    )

    manager = SourceManager()

    monkeypatch.setattr(
        "custom_components.virtual_device.source_manager.get_source_entities",
        lambda hass, label, device_class: [
            "sensor.power_1",
            "sensor.power_2",
        ],
    )

    manager.rebuild_virtual_device(
        hass,
        device,
    )

    assert manager.get_sources("power") == [
        "sensor.power_1",
        "sensor.power_2",
    ]

    monkeypatch.setattr(
        "custom_components.virtual_device.source_manager.get_source_entities",
        lambda hass, label, device_class: [
            "sensor.power_1",
        ],
    )

    state_1 = MagicMock()
    state_1.state = "100"
    state_1.attributes = {
        "device_class": "power",
        "unit_of_measurement": "W",
    }

    hass.states.get.side_effect = {
        "sensor.power_1": state_1,
    }.get

    await manager.async_reconcile(hass)

    assert manager.get_sources("power") == [
        "sensor.power_1",
    ]

    assert manager.get_source_values("power") == [
        SourceValue(
            entity_id="sensor.power_1",
            value=100.0,
            unit="W",
        ),
    ]


@pytest.mark.asyncio
async def test_reconcile_does_not_recreate_virtual_entity(
    monkeypatch,
) -> None:
    """Reconciliation changes sources, not the virtual entity."""
    hass = MagicMock()

    device = VirtualDevice(
        id="device-1",
        name="Energie",
        label_ref="label-id-energie",
        entities=[
            VirtualEntity(
                id="power",
                device_class="power",
                aggregation="sum",
            ),
        ],
    )

    manager = SourceManager()

    monkeypatch.setattr(
        "custom_components.virtual_device.source_manager.get_source_entities",
        lambda hass, label, device_class: [
            "sensor.power_1",
        ],
    )

    manager.rebuild_virtual_device(
        hass,
        device,
    )

    virtual_entity = device.entities[0]

    state = MagicMock()
    state.state = "100"
    state.attributes = {
        "device_class": "power",
        "unit_of_measurement": "W",
    }

    hass.states.get.return_value = state

    await manager.async_reconcile(hass)

    assert device.entities[0] is virtual_entity
    assert device.entities[0].id == "power"
    assert device.entities[0].device_class == "power"
    assert device.entities[0].aggregation == "sum"


def test_get_source_values_for_virtual_entity() -> None:
    """Return all cached source values for a virtual entity."""
    manager = SourceManager()

    manager.add_source(
        "power",
        "sensor.power_1",
    )
    manager.add_source(
        "power",
        "sensor.power_2",
    )

    manager.update_source_value(
        SourceValue(
            entity_id="sensor.power_1",
            value=100.0,
            unit="W",
        )
    )
    manager.update_source_value(
        SourceValue(
            entity_id="sensor.power_2",
            value=50.0,
            unit="W",
        )
    )

    values = manager.get_source_values(
        "power",
    )

    assert values == [
        SourceValue(
            entity_id="sensor.power_1",
            value=100.0,
            unit="W",
        ),
        SourceValue(
            entity_id="sensor.power_2",
            value=50.0,
            unit="W",
        ),
    ]


def test_updated_source_keeps_other_cached_values() -> None:
    """Updating one source keeps all other cached source values."""
    manager = SourceManager()

    manager.add_source(
        "power",
        "sensor.power_1",
    )
    manager.add_source(
        "power",
        "sensor.power_2",
    )

    manager.update_source_value(
        SourceValue(
            entity_id="sensor.power_1",
            value=100.0,
            unit="W",
        )
    )
    manager.update_source_value(
        SourceValue(
            entity_id="sensor.power_2",
            value=50.0,
            unit="W",
        )
    )

    # power_1 changes from 100 W to 120 W.
    manager.update_source_value(
        SourceValue(
            entity_id="sensor.power_1",
            value=120.0,
            unit="W",
        )
    )

    values = manager.get_source_values("power")

    assert values == [
        SourceValue(
            entity_id="sensor.power_1",
            value=120.0,
            unit="W",
        ),
        SourceValue(
            entity_id="sensor.power_2",
            value=50.0,
            unit="W",
        ),
    ]


@pytest.mark.asyncio
async def test_async_reconcile_reports_changed_virtual_entities(monkeypatch) -> None:
    """Report virtual entities whose source relationships changed."""
    hass = MagicMock()

    device = VirtualDevice(
        id="device-1",
        name="Beleuchtung",
        label_ref="label-id-beleuchtung",
        entities=[
            VirtualEntity(
                id="power",
                device_class="power",
                aggregation="sum",
            ),
        ],
    )

    from custom_components.virtual_device import source_manager

    monkeypatch.setattr(
        source_manager,
        "get_source_entities",
        lambda hass, label, device_class: [
            "sensor.power_1",
        ],
    )

    manager = SourceManager()
    manager.rebuild_virtual_device(hass, device)

    monkeypatch.setattr(
        source_manager,
        "get_source_entities",
        lambda hass, label, device_class: [
            "sensor.power_1",
            "sensor.power_2",
        ],
    )

    hass.states.get.side_effect = lambda entity_id: {
        "sensor.power_1": SimpleNamespace(
            state="100",
            attributes={"unit_of_measurement": "W"},
        ),
        "sensor.power_2": SimpleNamespace(
            state="50",
            attributes={"unit_of_measurement": "W"},
        ),
    }.get(entity_id)

    changed = await manager.async_reconcile(hass)

    assert changed == ["power"]
    assert manager.get_sources("power") == [
        "sensor.power_1",
        "sensor.power_2",
    ]


@pytest.mark.asyncio
async def test_async_reconciliation_calls_callback_for_changed_entities() -> None:
    """Notify the callback when source relationships change."""
    callback = MagicMock()
    manager = SourceManager(
        reconciliation_interval=0.01,
    )

    manager.async_reconcile = AsyncMock(
        return_value=["virtual_beleuchtung_power"],
    )
    manager._hass = MagicMock()
    manager._on_reconciliation = callback

    task = asyncio.create_task(
        manager._async_reconciliation_loop(),
    )

    await asyncio.sleep(0.02)

    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    callback.assert_called_with(
        ["virtual_beleuchtung_power"],
    )
