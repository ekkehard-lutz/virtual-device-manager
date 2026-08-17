"""Tests for Virtual Device Manager data models."""

from custom_components.virtual_device.models import (
    VirtualDevice,
    VirtualEntity,
)


def test_virtual_device_defaults() -> None:
    """Test VirtualDevice defaults."""
    device = VirtualDevice(
        id="test-device",
        label_ref="label-id-energie",
    )

    assert device.name is None
    assert device.entities == []


def test_virtual_entity_defaults() -> None:
    """Test VirtualEntity defaults."""
    entity = VirtualEntity(
        id="test-entity",
        device_class="power",
        aggregation="sum",
        unit="kW",
    )

    assert entity.name == "power"


def test_virtual_device_with_entity() -> None:
    """Test VirtualDevice with a virtual entity."""
    entity = VirtualEntity(
        id="test-entity",
        device_class="power",
        aggregation="sum",
        unit="kW",
    )

    device = VirtualDevice(
        id="test-device",
        name="Haus Energie",
        label_ref="label-id-energie",
        entities=[entity],
    )

    assert device.name == "Haus Energie"
    assert device.label_ref == "label-id-energie"
    assert len(device.entities) == 1
    assert device.entities[0].device_class == "power"

