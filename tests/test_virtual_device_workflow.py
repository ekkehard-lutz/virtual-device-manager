"""Tests for the virtual device workflow."""

from unittest.mock import MagicMock, patch

import pytest

from custom_components.virtual_device.models import (
    VirtualDevice,
    VirtualEntity,
)
from custom_components.virtual_device.virtual_device_workflow import (
    VirtualDeviceLabelConflict,
    add_virtual_entity,
    create_virtual_device,
    create_virtual_entity,
    delete_virtual_entity,
    generate_virtual_entity_id,
    update_virtual_device,
    update_virtual_entity,
    validate_virtual_entity,
)


def test_create_virtual_device_rejects_duplicate_label() -> None:
    """Reject a label already assigned to another virtual device."""
    hass = MagicMock()

    existing_device = VirtualDevice(
        id="virtual_label-id-energie",
        label_ref="label-id-energie",
    )

    label_entry = MagicMock()
    label_entry.label_id = "label-id-energie"
    label_entry.name = "Energie"

    label_registry = MagicMock()
    label_registry.async_get_label.return_value = label_entry

    with patch(
        "custom_components.virtual_device.virtual_device_workflow.label_registry.async_get",
        return_value=label_registry,
    ):
        with pytest.raises(VirtualDeviceLabelConflict):
            create_virtual_device(
                hass=hass,
                label_ref="label-id-energie",
                existing_virtual_devices=[existing_device],
            )


def test_create_virtual_device_rejects_unknown_label() -> None:
    """Reject a label reference that no longer exists."""
    hass = MagicMock()

    label_registry = MagicMock()
    label_registry.async_get_label.return_value = None

    with patch(
        "custom_components.virtual_device.virtual_device_workflow.label_registry.async_get",
        return_value=label_registry,
    ):
        with pytest.raises(ValueError, match="does not exist"):
            create_virtual_device(
                hass=hass,
                label_ref="label-id-missing",
                existing_virtual_devices=[],
            )


def test_update_virtual_device_keeps_label_unchanged() -> None:
    """Keep the original label when updating a virtual device."""
    hass = MagicMock()

    device = VirtualDevice(
        id="virtual_label-id-energie",
        label_ref="label-id-energie",
    )

    label_entry = MagicMock()
    label_entry.label_id = "label-id-energie"
    label_entry.name = "Energie"

    label_registry = MagicMock()
    label_registry.async_get_label.return_value = label_entry

    with patch(
        "custom_components.virtual_device.virtual_device_workflow."
        "label_registry.async_get",
        return_value=label_registry,
    ):
        with pytest.raises(ValueError, match="Label cannot be changed"):
            update_virtual_device(
                hass=hass,
                device=device,
                existing_virtual_devices=[device],
                label_ref="label-id-heizung",
            )


def test_update_virtual_device_keeps_id_when_label_is_unchanged() -> None:
    """Keep the same virtual device ID when the label does not change."""
    hass = MagicMock()

    device = VirtualDevice(
        id="virtual_label-id-energie",
        label_ref="label-id-energie",
    )

    label_entry = MagicMock()
    label_entry.label_id = "label-id-energie"
    label_entry.name = "Energie"

    label_registry = MagicMock()
    label_registry.async_get_label.return_value = label_entry

    with patch(
        "custom_components.virtual_device.virtual_device_workflow."
        "label_registry.async_get",
        return_value=label_registry,
    ):
        updated = update_virtual_device(
            hass=hass,
            device=device,
            existing_virtual_devices=[device],
        )

    assert updated.id == "virtual_label-id-energie"
    assert updated.label_ref == "label-id-energie"


def test_generate_virtual_entity_id_uses_base_id() -> None:
    """Use the base ID for the first entity of a device class."""
    entities = []

    result = generate_virtual_entity_id(
        "virtual_beleuchtung",
        "power",
        entities,
    )

    assert result == "virtual_beleuchtung_power"


def test_generate_virtual_entity_id_uses_suffix_for_second_entity() -> None:
    """Add a numeric suffix for a second entity of the same class."""
    entities = [
        VirtualEntity(
            id="virtual_beleuchtung_power",
            device_class="power",
            aggregation="sum",
        ),
    ]

    result = generate_virtual_entity_id(
        "virtual_beleuchtung",
        "power",
        entities,
    )

    assert result == "virtual_beleuchtung_power_1"


def test_generate_virtual_entity_id_uses_next_free_suffix() -> None:
    """Use the next available numeric suffix."""
    entities = [
        VirtualEntity(
            id="virtual_beleuchtung_power",
            device_class="power",
            aggregation="sum",
        ),
        VirtualEntity(
            id="virtual_beleuchtung_power_1",
            device_class="power",
            aggregation="avg",
        ),
    ]

    result = generate_virtual_entity_id(
        "virtual_beleuchtung",
        "power",
        entities,
    )

    assert result == "virtual_beleuchtung_power_2"


def test_generate_virtual_entity_id_different_device_class() -> None:
    """Different device classes use independent IDs."""
    entities = [
        VirtualEntity(
            id="virtual_beleuchtung_power",
            device_class="power",
            aggregation="sum",
        ),
    ]

    result = generate_virtual_entity_id(
        "virtual_beleuchtung",
        "energy",
        entities,
    )

    assert result == "virtual_beleuchtung_energy"


@pytest.mark.parametrize(
    "aggregation",
    [
        "sum",
        "avg",
        "min",
        "max",
    ],
)
def test_validate_virtual_entity_accepts_supported_aggregation(
    aggregation: str,
) -> None:
    """Accept all supported aggregation modes."""
    validate_virtual_entity(
        VirtualEntity(
            id="test",
            device_class="power",
            aggregation=aggregation,
        )
    )


def test_validate_virtual_entity_rejects_unsupported_aggregation() -> None:
    """Reject unsupported aggregation modes."""
    with pytest.raises(
        ValueError,
        match="Unsupported aggregation",
    ):
        validate_virtual_entity(
            VirtualEntity(
                id="test",
                device_class="power",
                aggregation="median",
            )
        )


def test_validate_virtual_entity_rejects_empty_device_class() -> None:
    """Reject an empty device class."""
    with pytest.raises(
        ValueError,
        match="Device class must not be empty",
    ):
        validate_virtual_entity(
            VirtualEntity(
                id="test",
                device_class="",
                aggregation="sum",
            )
        )


def test_create_virtual_entity_uses_base_id() -> None:
    """Use the base ID for the first entity of a device."""
    device = VirtualDevice(
        id="virtual_beleuchtung",
        label_ref="beleuchtung",
    )

    entity = create_virtual_entity(
        device=device,
        device_class="power",
        aggregation="sum",
    )

    assert entity.id == ("virtual_beleuchtung_power")
    assert entity.device_class == "power"
    assert entity.aggregation == "sum"
    assert not hasattr(entity, "unit")


def test_create_virtual_entity_uses_suffix() -> None:
    """Use a numeric suffix for a second entity."""
    device = VirtualDevice(
        id="virtual_beleuchtung",
        label_ref="beleuchtung",
        entities=[
            VirtualEntity(
                id="virtual_beleuchtung_power",
                device_class="power",
                aggregation="sum",
            ),
        ],
    )

    entity = create_virtual_entity(
        device=device,
        device_class="power",
        aggregation="avg",
    )

    assert entity.id == ("virtual_beleuchtung_power_1")


def test_create_virtual_entity_uses_base_id_for_different_class() -> None:
    """Use a separate base ID for another device class."""
    device = VirtualDevice(
        id="virtual_beleuchtung",
        label_ref="beleuchtung",
        entities=[
            VirtualEntity(
                id="virtual_beleuchtung_power",
                device_class="power",
                aggregation="sum",
            ),
        ],
    )

    entity = create_virtual_entity(
        device=device,
        device_class="energy",
        aggregation="sum",
    )

    assert entity.id == ("virtual_beleuchtung_energy")


def test_create_virtual_entity_uses_next_free_suffix() -> None:
    """Use the next available numeric suffix."""
    device = VirtualDevice(
        id="virtual_beleuchtung",
        label_ref="beleuchtung",
        entities=[
            VirtualEntity(
                id="virtual_beleuchtung_power",
                device_class="power",
                aggregation="sum",
            ),
            VirtualEntity(
                id="virtual_beleuchtung_power_1",
                device_class="power",
                aggregation="avg",
            ),
        ],
    )

    entity = create_virtual_entity(
        device=device,
        device_class="power",
        aggregation="max",
    )

    assert entity.id == ("virtual_beleuchtung_power_2")


def test_create_virtual_entity_does_not_modify_device() -> None:
    """Creating an entity does not modify the device."""
    device = VirtualDevice(
        id="virtual_beleuchtung",
        label_ref="beleuchtung",
    )

    entity = create_virtual_entity(
        device=device,
        device_class="power",
        aggregation="sum",
    )

    assert entity not in device.entities
    assert device.entities == []


def test_add_virtual_entity_adds_entity() -> None:
    """Add a new virtual entity to the device."""
    device = VirtualDevice(
        id="virtual_beleuchtung",
        label_ref="beleuchtung",
    )

    updated = add_virtual_entity(
        device=device,
        device_class="power",
        aggregation="sum",
    )

    assert len(updated.entities) == 1
    assert updated.entities[0].id == ("virtual_beleuchtung_power")


def test_add_virtual_entity_keeps_existing_entities() -> None:
    """Keep existing entities when adding a new one."""
    existing = VirtualEntity(
        id="virtual_beleuchtung_power",
        device_class="power",
        aggregation="sum",
    )

    device = VirtualDevice(
        id="virtual_beleuchtung",
        label_ref="beleuchtung",
        entities=[existing],
    )

    updated = add_virtual_entity(
        device=device,
        device_class="energy",
        aggregation="sum",
    )

    assert [entity.id for entity in updated.entities] == [
        "virtual_beleuchtung_power",
        "virtual_beleuchtung_energy",
    ]


def test_add_virtual_entity_does_not_modify_original_device() -> None:
    """Do not modify the original device."""
    device = VirtualDevice(
        id="virtual_beleuchtung",
        label_ref="beleuchtung",
    )

    updated = add_virtual_entity(
        device=device,
        device_class="power",
        aggregation="sum",
    )

    assert device.entities == []
    assert len(updated.entities) == 1
    assert updated is not device


def test_update_virtual_entity_keeps_id() -> None:
    """Keep the entity ID when updating an entity."""
    entity = VirtualEntity(
        id="virtual_beleuchtung_power_1",
        device_class="power",
        aggregation="sum",
    )

    device = VirtualDevice(
        id="virtual_beleuchtung",
        label_ref="beleuchtung",
        entities=[entity],
    )

    updated = update_virtual_entity(
        device=device,
        entity_id="virtual_beleuchtung_power_1",
    )

    assert updated.entities[0].id == ("virtual_beleuchtung_power_1")


def test_update_virtual_entity_rejects_unknown_entity() -> None:
    """Reject an unknown entity ID."""
    device = VirtualDevice(
        id="virtual_beleuchtung",
        label_ref="beleuchtung",
    )

    with pytest.raises(
        ValueError,
        match="Virtual entity .* does not exist",
    ):
        update_virtual_entity(
            device=device,
            entity_id="virtual_beleuchtung_power",
            aggregation="avg",
        )


def test_update_virtual_entity_validates_new_values() -> None:
    """Validate the resulting entity configuration."""
    entity = VirtualEntity(
        id="virtual_beleuchtung_power",
        device_class="power",
        aggregation="sum",
    )

    device = VirtualDevice(
        id="virtual_beleuchtung",
        label_ref="beleuchtung",
        entities=[entity],
    )

    with pytest.raises(
        ValueError,
        match="Unsupported aggregation",
    ):
        update_virtual_entity(
            device=device,
            entity_id="virtual_beleuchtung_power",
            aggregation="median",
        )


def test_delete_virtual_entity_removes_entity() -> None:
    """Remove an existing virtual entity."""
    entity = VirtualEntity(
        id="virtual_beleuchtung_power",
        device_class="power",
        aggregation="sum",
    )

    device = VirtualDevice(
        id="virtual_beleuchtung",
        label_ref="beleuchtung",
        entities=[entity],
    )

    updated = delete_virtual_entity(
        device,
        "virtual_beleuchtung_power",
    )

    assert updated.entities == []


def test_delete_virtual_entity_keeps_other_entities() -> None:
    """Keep all other virtual entities."""
    power = VirtualEntity(
        id="virtual_beleuchtung_power",
        device_class="power",
        aggregation="sum",
    )

    energy = VirtualEntity(
        id="virtual_beleuchtung_energy",
        device_class="energy",
        aggregation="sum",
    )

    device = VirtualDevice(
        id="virtual_beleuchtung",
        label_ref="beleuchtung",
        entities=[power, energy],
    )

    updated = delete_virtual_entity(
        device,
        "virtual_beleuchtung_power",
    )

    assert updated.entities == [energy]


def test_delete_virtual_entity_rejects_unknown_entity() -> None:
    """Reject an unknown entity ID."""
    device = VirtualDevice(
        id="virtual_beleuchtung",
        label_ref="beleuchtung",
    )

    with pytest.raises(
        ValueError,
        match="Virtual entity .* does not exist",
    ):
        delete_virtual_entity(
            device,
            "virtual_beleuchtung_power",
        )


def test_delete_virtual_entity_does_not_modify_original() -> None:
    """Do not modify the original device."""
    entity = VirtualEntity(
        id="virtual_beleuchtung_power",
        device_class="power",
        aggregation="sum",
    )

    device = VirtualDevice(
        id="virtual_beleuchtung",
        label_ref="beleuchtung",
        entities=[entity],
    )

    updated = delete_virtual_entity(
        device,
        "virtual_beleuchtung_power",
    )

    assert device.entities == [entity]
    assert updated.entities == []
    assert updated is not device


def test_update_virtual_entity_keeps_device_class() -> None:
    """Device class cannot be changed when updating an entity."""
    entity = VirtualEntity(
        id="virtual_beleuchtung_power",
        device_class="power",
        aggregation="sum",
    )

    device = VirtualDevice(
        id="virtual_beleuchtung",
        label_ref="beleuchtung",
        entities=[entity],
    )

    updated = update_virtual_entity(
        device=device,
        entity_id="virtual_beleuchtung_power",
        aggregation="avg",
    )

    assert updated.entities[0].device_class == "power"
    assert updated.entities[0].aggregation == "avg"
