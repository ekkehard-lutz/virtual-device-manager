"""Tests for Recorder-independent history aggregation."""

from datetime import UTC, datetime, timedelta

import pytest

from custom_components.virtual_device.history.aggregator import (
    HistoricalAggregator,
    RawTimelineState,
)
from custom_components.virtual_device.history.models import (
    RawSourceEvent,
    StatisticsSlot,
)

BASE = datetime(2026, 1, 1, 12, tzinfo=UTC)


def event(entity_id: str, minute: int, value, unit: str | None = "W"):
    return RawSourceEvent(entity_id, BASE + timedelta(minutes=minute), value, unit)


@pytest.mark.parametrize(
    ("aggregation", "expected"),
    [
        ("sum", [15, 25, 35, 45]),
        ("avg", [7.5, 12.5, 17.5, 22.5]),
        ("min", [5, 5, 15, 15]),
        ("max", [10, 20, 20, 30]),
    ],
)
def test_raw_union_timeline(aggregation, expected) -> None:
    events = (
        event("sensor.a", 0, 10),
        event("sensor.a", 4, 20),
        event("sensor.a", 11, 30),
        event("sensor.b", 0, 5),
        event("sensor.b", 7, 15),
    )

    points, _ = HistoricalAggregator().aggregate_raw(events, "power", aggregation)

    assert [point.timestamp for point in points] == [
        BASE,
        BASE + timedelta(minutes=4),
        BASE + timedelta(minutes=7),
        BASE + timedelta(minutes=11),
    ]
    assert [point.value for point in points] == pytest.approx(expected)


def test_source_appears_later_without_zero() -> None:
    points, _ = HistoricalAggregator().aggregate_raw(
        (event("sensor.a", 0, 100), event("sensor.b", 5, 200)),
        "power",
        "avg",
    )

    assert [point.value for point in points] == [100, 150]


def test_raw_median_uses_currently_valid_sources() -> None:
    events = (
        event("sensor.a", 0, 20, "°C"),
        event("sensor.b", 0, 22, "°C"),
        event("sensor.c", 0, 30, "°C"),
        event("sensor.c", 5, None, None),
        event("sensor.a", 10, 21, "°C"),
        event("sensor.c", 15, 23, "°C"),
    )

    points, _ = HistoricalAggregator().aggregate_raw(
        events, "temperature", "median"
    )

    assert [point.timestamp for point in points] == [
        BASE,
        BASE + timedelta(minutes=5),
        BASE + timedelta(minutes=10),
        BASE + timedelta(minutes=15),
    ]
    assert [point.value for point in points] == [22, 21, 21.5, 22]


@pytest.mark.parametrize("invalid_value", [None])
def test_invalid_period_removes_source(invalid_value) -> None:
    points, _ = HistoricalAggregator().aggregate_raw(
        (
            event("sensor.a", 0, 10),
            event("sensor.b", 0, 5),
            event("sensor.a", 1, invalid_value, None),
            event("sensor.a", 2, 20),
        ),
        "power",
        "sum",
    )

    assert [point.value for point in points] == [15, 5, 25]


def test_raw_unit_conversion() -> None:
    points, _ = HistoricalAggregator().aggregate_raw(
        (event("sensor.a", 0, 500, "W"), event("sensor.b", 0, 1, "kW")),
        "power",
        "sum",
    )

    assert points[0].value == 1500


def test_cross_chunk_continuity_and_boundary_deduplication() -> None:
    aggregator = HistoricalAggregator()
    first, carry = aggregator.aggregate_raw(
        (event("sensor.a", 0, 10), event("sensor.b", 1, 5)), "power", "sum"
    )
    second, carry = aggregator.aggregate_raw(
        (
            event("sensor.a", 1, 10),
            event("sensor.a", 2, 20),
        ),
        "power",
        "sum",
        carry,
    )

    assert isinstance(carry, RawTimelineState)
    assert [point.value for point in first + second] == [10, 15, 25]


@pytest.mark.parametrize(
    ("aggregation", "mean", "minimum", "maximum", "state", "sum_value"),
    [
        ("sum", 45, 40, 54, 50, 300),
        ("avg", 22.5, 20, 27, 25, 150),
        ("min", 20, 18, 24, 20, 100),
        ("max", 25, 22, 30, 30, 200),
    ],
)
def test_statistics_are_aggregated_field_wise(
    aggregation, mean, minimum, maximum, state, sum_value
) -> None:
    slots = (
        StatisticsSlot("sensor.a", BASE, "W", 20, 18, 24, 20, 100),
        StatisticsSlot("sensor.b", BASE, "W", 25, 22, 30, 30, 200),
    )

    result = HistoricalAggregator().aggregate_statistics(
        slots, "sensor.virtual_power", "power", aggregation, BASE + timedelta(hours=1)
    )

    assert len(result) == 1
    assert result[0].mean == mean
    assert result[0].minimum == minimum
    assert result[0].maximum == maximum
    assert result[0].state == state
    assert result[0].sum == sum_value


def test_statistics_missing_fields_are_omitted_not_zero() -> None:
    slots = (
        StatisticsSlot("sensor.a", BASE, "W", mean=100),
        StatisticsSlot("sensor.b", BASE, "W", minimum=20),
    )

    result = HistoricalAggregator().aggregate_statistics(
        slots, "sensor.virtual_power", "power", "avg", BASE + timedelta(hours=1)
    )

    assert result[0].mean == 100
    assert result[0].minimum == 20
    assert result[0].maximum is None


def test_statistics_convert_units_and_exclude_incomplete_slot() -> None:
    slots = (
        StatisticsSlot("sensor.a", BASE, "W", mean=500),
        StatisticsSlot("sensor.b", BASE, "kW", mean=1),
        StatisticsSlot("sensor.a", BASE + timedelta(minutes=5), "W", mean=999),
    )

    result = HistoricalAggregator().aggregate_statistics(
        slots,
        "sensor.virtual_power",
        "power",
        "sum",
        BASE + timedelta(minutes=5),
    )

    assert len(result) == 1
    assert result[0].mean == 1500


def test_energy_statistics_convert_kwh_to_wh() -> None:
    result = HistoricalAggregator().aggregate_statistics(
        (
            StatisticsSlot("sensor.a", BASE, "Wh", sum=500),
            StatisticsSlot("sensor.b", BASE, "kWh", sum=1),
        ),
        "sensor.virtual_energy",
        "energy",
        "sum",
        BASE + timedelta(hours=1),
    )

    assert result[0].sum == 1500


def test_measurement_statistics_use_field_wise_median() -> None:
    slots = (
        StatisticsSlot("sensor.a", BASE, "°C", mean=20, minimum=18, maximum=22),
        StatisticsSlot("sensor.b", BASE, "°C", mean=22, minimum=21, maximum=25),
        StatisticsSlot("sensor.c", BASE, "°C", mean=24, minimum=19, maximum=27),
    )

    result = HistoricalAggregator().aggregate_statistics(
        slots,
        "sensor.indoor_temperature",
        "temperature",
        "median",
        BASE + timedelta(minutes=5),
    )

    assert (result[0].mean, result[0].minimum, result[0].maximum) == (22, 19, 25)


def test_statistics_median_omits_missing_fields() -> None:
    result = HistoricalAggregator().aggregate_statistics(
        (
            StatisticsSlot("sensor.a", BASE, "V", mean=1, minimum=0.9),
            StatisticsSlot("sensor.b", BASE, "V", mean=3, maximum=3.1),
            StatisticsSlot("sensor.c", BASE, "V", mean=2),
        ),
        "sensor.virtual_voltage",
        "voltage",
        "median",
        BASE + timedelta(hours=1),
    )

    assert result[0].mean == 2
    assert result[0].minimum == 0.9
    assert result[0].maximum == 3.1
