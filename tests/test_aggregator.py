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


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ([1, 2, 3], 2),
        ([1, 2, 3, 4], 2.5),
        ([7], 7),
    ],
)
def test_median(values, expected) -> None:
    sources = [
        SourceValue(f"sensor.{index}", value, "W")
        for index, value in enumerate(values)
    ]

    assert aggregate_values(sources, "power", "median") == expected


def test_median_empty_values() -> None:
    assert aggregate_values([], "temperature", "median") is None


def test_temperature_median_normalizes_mixed_units() -> None:
    values = [
        SourceValue("sensor.c", 20, "°C"),
        SourceValue("sensor.f", 69.8, "°F"),
        SourceValue("sensor.k", 294.15, "K"),
    ]

    assert aggregate_values(values, "temperature", "median") == pytest.approx(21)


@pytest.mark.parametrize("device_class", ["voltage", "current"])
def test_scaled_electrical_median(device_class) -> None:
    units = ("mV", "V", "kV") if device_class == "voltage" else ("mA", "A", "kA")
    values = [
        SourceValue("sensor.small", 1000, units[0]),
        SourceValue("sensor.native", 1, units[1]),
        SourceValue("sensor.large", 0.001, units[2]),
    ]

    assert aggregate_values(values, device_class, "median") == pytest.approx(1)


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
