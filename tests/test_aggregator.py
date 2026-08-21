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
    )

    assert result == 2000.0


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
    )

    assert result == pytest.approx(666.6666666667)


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
    )

    assert result == 500.0


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
    )

    assert result == 1000.0


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
    )

    assert result == 500.0


def test_empty_values() -> None:
    """Test aggregation without source values."""
    result = aggregate_values(
        [],
        device_class="power",
        aggregation="sum",
    )

    assert result is None


def test_power_aggregation_uses_native_unit() -> None:
    """Test power aggregation uses the VDM native unit."""
    values = [
        SourceValue("sensor.test_1", 1, "kW"),
        SourceValue("sensor.test_2", 500, "W"),
    ]

    result = aggregate_values(
        values,
        device_class="power",
        aggregation="sum",
    )

    assert result == 1500.0
