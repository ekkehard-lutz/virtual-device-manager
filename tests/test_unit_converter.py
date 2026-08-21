"""Tests for Virtual Device Manager unit conversion."""

import pytest

from custom_components.virtual_device.unit_converter import (
    convert_value,
)


def test_same_unit() -> None:
    """Test conversion with identical units."""
    assert convert_value(123.4, "power", "W", "W") == 123.4


def test_watt_to_kw() -> None:
    """Test W to kW conversion."""
    assert convert_value(1000, "power", "W", "kW") == 1.0


def test_kw_to_watt() -> None:
    """Test kW to W conversion."""
    assert convert_value(2.5, "power", "kW", "W") == 2500.0


def test_mw_to_kw() -> None:
    """Test MW to kW conversion."""
    assert convert_value(3, "power", "MW", "kW") == 3000.0


def test_gwh_to_mwh() -> None:
    """Test GWh to MWh conversion."""
    assert convert_value(1.2, "energy", "GWh", "MWh") == 1200.0


def test_mwh_to_kwh() -> None:
    """Test MWh to kWh conversion."""
    assert convert_value(2, "energy", "MWh", "kWh") == 2000.0


def test_incompatible_device_class() -> None:
    """Test incompatible device class and units."""
    with pytest.raises(ValueError):
        convert_value(100, "power", "W", "kWh")


def test_invalid_unit() -> None:
    """Test invalid unit."""
    with pytest.raises(ValueError):
        convert_value(100, "power", "W", "foobar")


def test_zero_conversion() -> None:
    """Test conversion of zero."""
    assert convert_value(0, "power", "W", "kW") == 0.0


def test_negative_conversion() -> None:
    """Test conversion of negative values."""
    assert convert_value(-500, "power", "W", "kW") == -0.5


def test_decimal_conversion() -> None:
    """Test conversion of decimal values."""
    assert convert_value(0.123, "power", "kW", "W") == 123.0


def test_milliwatt_to_watt() -> None:
    """Test mW to W conversion."""
    assert convert_value(5000, "power", "mW", "W") == 5.0


def test_celsius_to_fahrenheit() -> None:
    """Test temperature conversion via Home Assistant."""
    result = convert_value(20, "temperature", "°C", "°F")

    assert result == pytest.approx(68.0)


def test_fahrenheit_to_celsius() -> None:
    """Test temperature conversion via Home Assistant."""
    result = convert_value(68, "temperature", "°F", "°C")

    assert result == pytest.approx(20.0)


def test_missing_device_class_converter() -> None:
    """Test missing Home Assistant unit converter."""
    with pytest.raises(ValueError, match="No unit converter"):
        convert_value(100, "foobar", "W", "kW")
