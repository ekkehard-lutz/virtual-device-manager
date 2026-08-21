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
    )

    assert entity.name == "power"


def test_virtual_device_with_entity() -> None:
    """Test VirtualDevice with a virtual entity."""
    entity = VirtualEntity(
        id="test-entity",
        device_class="power",
        aggregation="sum",
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


def test_virtual_entity_has_no_configured_unit() -> None:
    """Virtual entity does not contain a configured unit."""
    entity = VirtualEntity(
        id="test",
        device_class="power",
        aggregation="sum",
    )

    assert not hasattr(entity, "unit")
