"""Tests for safe hourly-only history persistence."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from custom_components.virtual_device.history.models import StatisticsSlot
from custom_components.virtual_device.history.persistence import (
    HistoryPersistenceAdapter,
    StatisticMeanType,
)

BASE = datetime(2026, 1, 1, 12, tzinfo=UTC)


def test_energy_hourly_import_metadata_and_fields() -> None:
    hass = MagicMock()
    slots = (StatisticsSlot("sensor.virtual_energy", BASE, "Wh", state=100, sum=75),)

    with patch(
        "custom_components.virtual_device.history.persistence.async_import_statistics"
    ) as import_statistics:
        count = HistoryPersistenceAdapter(hass).async_upsert_hourly(
            "sensor.virtual_energy", "energy", slots
        )

    assert count == 1
    metadata, data = import_statistics.call_args.args[1:]
    assert metadata["statistic_id"] == "sensor.virtual_energy"
    assert metadata["source"] == "recorder"
    assert metadata["unit_of_measurement"] == "Wh"
    assert metadata["unit_class"] == "energy"
    assert metadata["mean_type"] is StatisticMeanType.NONE
    assert metadata["has_sum"] is True
    assert data == [{"start": BASE, "state": 100, "sum": 75}]


def test_power_hourly_import_metadata_and_fields() -> None:
    hass = MagicMock()
    slots = (
        StatisticsSlot(
            "sensor.virtual_power", BASE, "W", mean=10, minimum=5, maximum=15
        ),
    )

    with patch(
        "custom_components.virtual_device.history.persistence.async_import_statistics"
    ) as import_statistics:
        HistoryPersistenceAdapter(hass).async_upsert_hourly(
            "sensor.virtual_power", "power", slots
        )

    metadata, data = import_statistics.call_args.args[1:]
    assert metadata["unit_class"] == "power"
    assert metadata["mean_type"] is StatisticMeanType.ARITHMETIC
    assert metadata["has_sum"] is False
    assert data == [{"start": BASE, "mean": 10, "min": 5, "max": 15}]


def test_empty_hourly_result_does_not_import() -> None:
    with patch(
        "custom_components.virtual_device.history.persistence.async_import_statistics"
    ) as import_statistics:
        count = HistoryPersistenceAdapter(MagicMock()).async_upsert_hourly(
            "sensor.virtual_power", "power", ()
        )

    assert count == 0
    import_statistics.assert_not_called()


@pytest.mark.parametrize(
    ("device_class", "unit", "unit_class"),
    [
        ("temperature", "°C", "temperature"),
        ("voltage", "V", "voltage"),
        ("current", "A", "electric_current"),
    ],
)
def test_new_measurement_hourly_metadata(device_class, unit, unit_class) -> None:
    slot = StatisticsSlot(
        f"sensor.virtual_{device_class}",
        BASE,
        unit,
        mean=10,
        minimum=9,
        maximum=11,
    )

    with patch(
        "custom_components.virtual_device.history.persistence.async_import_statistics"
    ) as import_statistics:
        HistoryPersistenceAdapter(MagicMock()).async_upsert_hourly(
            slot.entity_id, device_class, (slot,)
        )

    metadata = import_statistics.call_args.args[1]
    assert metadata["unit_of_measurement"] == unit
    assert metadata["unit_class"] == unit_class
    assert metadata["mean_type"] is StatisticMeanType.ARITHMETIC
    assert metadata["has_sum"] is False


def test_resync_only_upserts_new_calculation_and_never_clears() -> None:
    """V1 cannot delete an obsolete 2024 slot absent from recalculation."""
    recalculated = (
        StatisticsSlot("sensor.virtual_energy", BASE, "Wh", sum=200),
        StatisticsSlot(
            "sensor.virtual_energy", BASE + timedelta(hours=1), "Wh", sum=300
        ),
    )

    with patch(
        "custom_components.virtual_device.history.persistence.async_import_statistics"
    ) as import_statistics:
        HistoryPersistenceAdapter(MagicMock()).async_upsert_hourly(
            "sensor.virtual_energy", "energy", recalculated
        )

    imported = import_statistics.call_args.args[2]
    assert [row["start"] for row in imported] == [
        BASE,
        BASE + timedelta(hours=1),
    ]
    # There is intentionally no clear/delete call or representation of an
    # older absent slot. Home Assistant safely upserts only these rows.
