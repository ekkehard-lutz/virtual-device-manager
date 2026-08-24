"""Tests for Virtual Device Manager validation."""

import pytest

from custom_components.virtual_device.const import SUPPORTED_DEVICE_CLASSES
from custom_components.virtual_device.models import (
    VirtualDevice,
    VirtualEntity,
)
from custom_components.virtual_device.validation import (
    ValidationError,
    can_convert_unit,
    is_valid_aggregation,
    is_valid_device_class,
    is_valid_unit_for_device_class,
    validate_virtual_device,
    validate_virtual_entity,
)


def test_valid_device_class() -> None:
    """Test supported device classes."""
    assert is_valid_device_class("power")
    assert is_valid_device_class("energy")


def test_invalid_device_class() -> None:
    """Test unsupported device class."""
    assert not is_valid_device_class("foobar")


def test_device_class_has_native_unit() -> None:
    """Test native units for supported device classes."""
    assert SUPPORTED_DEVICE_CLASSES["power"] == "W"
    assert SUPPORTED_DEVICE_CLASSES["energy"] == "Wh"


def test_valid_power_unit() -> None:
    """Test valid power unit."""
    assert is_valid_unit_for_device_class("power", "W")
    assert is_valid_unit_for_device_class("power", "kW")
    assert is_valid_unit_for_device_class("power", "MW")


def test_invalid_power_unit() -> None:
    """Test invalid power unit."""
    assert not is_valid_unit_for_device_class("power", "kWh")


def test_valid_energy_unit() -> None:
    """Test valid energy unit."""
    assert is_valid_unit_for_device_class("energy", "Wh")
    assert is_valid_unit_for_device_class("energy", "kWh")
    assert is_valid_unit_for_device_class("energy", "MWh")


def test_invalid_device_class_unit_combination() -> None:
    """Test incompatible device class and unit."""
    assert not is_valid_unit_for_device_class("temperature", "kW")


def test_power_unit_conversion() -> None:
    """Test power unit conversion compatibility."""
    assert can_convert_unit("power", "W", "kW")
    assert can_convert_unit("power", "kW", "MW")
    assert can_convert_unit("power", "MW", "W")


def test_energy_unit_conversion() -> None:
    """Test energy unit conversion compatibility."""
    assert can_convert_unit("energy", "Wh", "kWh")
    assert can_convert_unit("energy", "kWh", "MWh")


def test_incompatible_unit_conversion() -> None:
    """Test incompatible unit conversion."""
    assert not can_convert_unit("power", "W", "kWh")


def test_valid_aggregations() -> None:
    """Test supported aggregation methods."""
    assert is_valid_aggregation("sum")
    assert is_valid_aggregation("avg")
    assert is_valid_aggregation("min")
    assert is_valid_aggregation("max")


def test_invalid_aggregation() -> None:
    """Test unsupported aggregation methods."""
    assert not is_valid_aggregation("mode")
    assert not is_valid_aggregation("SUM")
    assert not is_valid_aggregation("")


def test_valid_virtual_entity() -> None:
    """Test a valid virtual entity."""
    entity = VirtualEntity(
        id="test",
        device_class="power",
        aggregation="sum",
    )

    validate_virtual_entity(entity)


def test_invalid_virtual_entity_device_class() -> None:
    """Test unsupported device class."""
    entity = VirtualEntity(
        id="test",
        device_class="foobar",
        aggregation="sum",
    )

    with pytest.raises(
        ValidationError,
        match="Unsupported device class",
    ):
        validate_virtual_entity(entity)


def test_invalid_virtual_entity_aggregation() -> None:
    """Test invalid aggregation."""
    entity = VirtualEntity(
        id="test",
        device_class="power",
        aggregation="mode",
    )

    with pytest.raises(ValidationError, match="Unsupported aggregation"):
        validate_virtual_entity(entity)


def test_valid_virtual_device() -> None:
    """Test a valid virtual device."""
    device = VirtualDevice(
        id="device",
        label_ref="label-id-energie",
        entities=[
            VirtualEntity(
                id="power",
                device_class="power",
                aggregation="sum",
            ),
        ],
    )

    validate_virtual_device(device)


def test_empty_virtual_device() -> None:
    """Test a virtual device without entities."""
    device = VirtualDevice(
        id="device",
        label_ref="label-id-energie",
    )

    validate_virtual_device(device)


def test_virtual_device_without_label() -> None:
    """Test virtual device without a label."""
    device = VirtualDevice(
        id="device",
        label_ref="",
    )

    with pytest.raises(ValidationError, match="Label must not be empty"):
        validate_virtual_device(device)


def test_duplicate_virtual_entity_id() -> None:
    """Test duplicate virtual entity IDs."""
    entity1 = VirtualEntity(
        id="power",
        device_class="power",
        aggregation="sum",
    )

    entity2 = VirtualEntity(
        id="power",
        device_class="power",
        aggregation="max",
    )

    device = VirtualDevice(
        id="device",
        label_ref="label-id-energie",
        entities=[entity1, entity2],
    )

    with pytest.raises(
        ValidationError,
        match="Duplicate virtual entity ID",
    ):
        validate_virtual_device(device)
