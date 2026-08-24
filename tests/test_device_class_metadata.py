"""Tests for centralized device-class metadata."""

from homeassistant.components.sensor import SensorStateClass

from custom_components.virtual_device.device_class_metadata import (
    DEVICE_CLASS_METADATA,
    get_device_class_metadata,
)


def test_energy_metadata() -> None:
    metadata = get_device_class_metadata("energy")

    assert metadata.native_unit == "Wh"
    assert metadata.state_class is SensorStateClass.TOTAL_INCREASING


def test_power_metadata() -> None:
    metadata = get_device_class_metadata("power")

    assert metadata.native_unit == "W"
    assert metadata.state_class is SensorStateClass.MEASUREMENT


def test_metadata_is_single_supported_device_class_source() -> None:
    assert set(DEVICE_CLASS_METADATA) == {"energy", "power"}
