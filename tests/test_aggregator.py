"""Tests for Virtual Device Manager aggregation."""

import pytest

from custom_components.virtual_device.aggregator import (
    SourceValue,
    aggregate_values,
)


def test_sum() -> None:
    """Test sum aggregation."""
    values = [
        SourceValue("sensor.test_1", 500, "W"),
        SourceValue("sensor.test_2", 1.0, "kW"),
        SourceValue("sensor.test_3", 500, "W"),
    ]

    result = aggregate_values(
        values,
        device_class="power",
        aggregation="sum",
        target_unit="kW",
    )

    assert result == 2.0


def test_average() -> None:
    """Test average aggregation."""
    values = [
        SourceValue("sensor.test_1", 500, "W"),
        SourceValue("sensor.test_2", 1.0, "kW"),
        SourceValue("sensor.test_3", 500, "W"),
    ]

    result = aggregate_values(
        values,
        device_class="power",
        aggregation="avg",
        target_unit="kW",
    )

    assert result == pytest.approx(0.6666666667)


def test_minimum() -> None:
    """Test minimum aggregation."""
    values = [
        SourceValue("sensor.test_1", 500, "W"),
        SourceValue("sensor.test_2", 1.0, "kW"),
        SourceValue("sensor.test_3", 500, "W"),
    ]

    result = aggregate_values(
        values,
        device_class="power",
        aggregation="min",
        target_unit="kW",
    )

    assert result == 0.5


def test_maximum() -> None:
    """Test maximum aggregation."""
    values = [
        SourceValue("sensor.test_1", 500, "W"),
        SourceValue("sensor.test_2", 1.0, "kW"),
        SourceValue("sensor.test_3", 500, "W"),
    ]

    result = aggregate_values(
        values,
        device_class="power",
        aggregation="max",
        target_unit="kW",
    )

    assert result == 1.0


def test_negative_values() -> None:
    """Test aggregation with negative values."""
    values = [
        SourceValue("sensor.test_1", -500, "W"),
        SourceValue("sensor.test_2", 1.0, "kW"),
    ]

    result = aggregate_values(
        values,
        device_class="power",
        aggregation="sum",
        target_unit="kW",
    )

    assert result == 0.5


def test_empty_values() -> None:
    """Test aggregation without source values."""
    result = aggregate_values(
        [],
        device_class="power",
        aggregation="sum",
        target_unit="kW",
    )

    assert result is None
