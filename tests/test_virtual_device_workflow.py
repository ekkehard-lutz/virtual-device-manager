"""Tests for the virtual device workflow."""

from unittest.mock import MagicMock, patch

import pytest

from custom_components.virtual_device.models import (
    VirtualDevice,
    VirtualEntity,
)
from custom_components.virtual_device.virtual_device_workflow import (
    PhysicalDeviceNameConflict,
    VirtualDeviceLabelConflict,
    VirtualDeviceNameConflict,
    add_virtual_entity,
    create_virtual_device,
    create_virtual_entity,
    delete_virtual_entity,
    generate_virtual_entity_id,
    has_physical_device_name_conflict,
    update_virtual_device,
    update_virtual_entity,
    validate_virtual_entity,
)


def test_create_virtual_device_uses_label_name_as_default() -> None:
    """Use the current label name when no device name is given."""
    hass = MagicMock()

    label_entry = MagicMock()
    label_entry.label_id = "label-id-energie"
    label_entry.name = "Energie"

    label_registry = MagicMock()
    label_registry.async_get_label.return_value = label_entry

    with patch(
        "custom_components.virtual_device.virtual_device_workflow.label_registry.async_get",
        return_value=label_registry,
    ):
        device = create_virtual_device(
            hass=hass,
            label_ref="label-id-energie",
            name=None,
            existing_virtual_devices=[],
        )

    assert isinstance(device, VirtualDevice)
    assert device.label_ref == "label-id-energie"
    assert device.name == "Energie"


def test_create_virtual_device_uses_explicit_name() -> None:
    """Use the explicitly configured device name."""
    hass = MagicMock()

    label_entry = MagicMock()
    label_entry.label_id = "label-id-energie"
    label_entry.name = "Energie"

    label_registry = MagicMock()
    label_registry.async_get_label.return_value = label_entry

    with patch(
        "custom_components.virtual_device.virtual_device_workflow.label_registry.async_get",
        return_value=label_registry,
    ):
        device = create_virtual_device(
            hass=hass,
            label_ref="label-id-energie",
            name="Haus Energie",
            existing_virtual_devices=[],
        )

    assert device.name == "Haus Energie"


def test_create_virtual_device_rejects_duplicate_virtual_device_name() -> None:
    """Reject a name already used by another virtual device."""
    hass = MagicMock()

    existing_device = VirtualDevice(
        id="device-1",
        label_ref="label-id-alt",
        name="Haus Energie",
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
        with pytest.raises(VirtualDeviceNameConflict):
            create_virtual_device(
                hass=hass,
                label_ref="label-id-energie",
                name="Haus Energie",
                existing_virtual_devices=[existing_device],
            )


def test_create_virtual_device_rejects_duplicate_label() -> None:
    """Reject a label already assigned to another virtual device."""
    hass = MagicMock()

    existing_device = VirtualDevice(
        id="virtual_label-id-energie",
        label_ref="label-id-energie",
        name="Energie",
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
                name="Haus Energie",
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
                name=None,
                existing_virtual_devices=[],
            )


def test_physical_device_name_conflict_is_detected() -> None:
    """Detect a physical device with the same name."""
    hass = MagicMock()

    physical_device = MagicMock()
    physical_device.name = "Haus Energie"

    device_registry = MagicMock()
    device_registry.devices.values.return_value = [physical_device]

    with patch(
        "custom_components.virtual_device.virtual_device_workflow.device_registry.async_get",
        return_value=device_registry,
    ):
        assert has_physical_device_name_conflict(
            hass,
            "Haus Energie",
        )


def test_physical_device_name_conflict_is_not_reported_for_different_name() -> None:
    """Do not report a physical device with another name."""
    hass = MagicMock()

    physical_device = MagicMock()
    physical_device.name = "Haus Heizung"

    device_registry = MagicMock()
    device_registry.devices.values.return_value = [physical_device]

    with patch(
        "custom_components.virtual_device.virtual_device_workflow.device_registry.async_get",
        return_value=device_registry,
    ):
        assert not has_physical_device_name_conflict(
            hass,
            "Haus Energie",
        )


def test_create_virtual_device_requires_confirmation_for_physical_name_conflict() -> None:
    """Require confirmation when a physical device has the same name."""
    hass = MagicMock()

    label_entry = MagicMock()
    label_entry.label_id = "label-id-energie"
    label_entry.name = "Energie"

    label_registry = MagicMock()
    label_registry.async_get_label.return_value = label_entry

    with patch(
        "custom_components.virtual_device.virtual_device_workflow.label_registry.async_get",
        return_value=label_registry,
    ):
        with patch(
            "custom_components.virtual_device.virtual_device_workflow.has_physical_device_name_conflict",
            return_value=True,
        ):
            with pytest.raises(PhysicalDeviceNameConflict):
                create_virtual_device(
                    hass=hass,
                    label_ref="label-id-energie",
                    name="Haus Energie",
                    existing_virtual_devices=[],
                )


def test_update_virtual_device_keeps_same_name() -> None:
    """Allow keeping the current virtual device name."""
    hass = MagicMock()

    device = VirtualDevice(
        id="virtual_label-id-energie",
        label_ref="label-id-energie",
        name="Haus Energie",
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
        updated = update_virtual_device(
            hass=hass,
            device=device,
            existing_virtual_devices=[device],
            name="Haus Energie",
        )

    assert updated.id == "virtual_label-id-energie"
    assert updated.name == "Haus Energie"
    assert updated.label_ref == "label-id-energie"


def test_update_virtual_device_keeps_id_when_label_changes() -> None:
    """Allow moving a virtual device to another label."""
    hass = MagicMock()

    device = VirtualDevice(
        id="virtual_label-id-energie",
        label_ref="label-id-energie",
        name="Haus Energie",
    )

    label_entry = MagicMock()
    label_entry.label_id = "label-id-heizung"
    label_entry.name = "Heizung"

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
            label_ref="label-id-heizung",
        )

    assert updated.id == "virtual_label-id-energie"
    assert updated.name == "Haus Energie"
    assert updated.label_ref == "label-id-heizung"


def test_update_virtual_device_keeps_id_when_label_is_unchanged() -> None:
    """Keep the same virtual device ID when the label does not change."""
    hass = MagicMock()

    device = VirtualDevice(
        id="virtual_label-id-energie",
        label_ref="label-id-energie",
        name="Haus Energie",
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
            name="Neue Energie",
        )

    assert updated.id == "virtual_label-id-energie"
    assert updated.label_ref == "label-id-energie"
    assert updated.name == "Neue Energie"


def test_update_virtual_device_rejects_other_virtual_device_label() -> None:
    """Reject moving to a label assigned to another virtual device."""
    hass = MagicMock()

    device = VirtualDevice(
        id="device-1",
        label_ref="label-id-energie",
        name="Haus Energie",
    )

    other_device = VirtualDevice(
        id="device-2",
        label_ref="label-id-heizung",
        name="Heizung",
    )

    label_entry = MagicMock()
    label_entry.label_id = "label-id-heizung"
    label_entry.name = "Heizung"

    label_registry = MagicMock()
    label_registry.async_get_label.return_value = label_entry

    with patch(
        "custom_components.virtual_device.virtual_device_workflow.label_registry.async_get",
        return_value=label_registry,
    ):
        with pytest.raises(VirtualDeviceLabelConflict):
            update_virtual_device(
                hass=hass,
                device=device,
                existing_virtual_devices=[
                    device,
                    other_device,
                ],
                label_ref="label-id-heizung",
            )


def test_update_virtual_device_rejects_other_virtual_device_name() -> None:
    """Reject a name already used by another virtual device."""
    hass = MagicMock()

    device = VirtualDevice(
        id="device-1",
        label_ref="label-id-energie",
        name="Haus Energie",
    )

    other_device = VirtualDevice(
        id="device-2",
        label_ref="label-id-heizung",
        name="Heizung",
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
        with pytest.raises(VirtualDeviceNameConflict):
            update_virtual_device(
                hass=hass,
                device=device,
                existing_virtual_devices=[
                    device,
                    other_device,
                ],
                name="Heizung",
            )


def test_update_virtual_device_requires_confirmation_for_physical_name_conflict() -> None:
    """Require confirmation when renaming to a physical device name."""
    hass = MagicMock()

    device = VirtualDevice(
        id="device-1",
        label_ref="label-id-energie",
        name="Haus Energie",
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
        with patch(
            "custom_components.virtual_device.virtual_device_workflow.has_physical_device_name_conflict",
            return_value=True,
        ):
            with pytest.raises(PhysicalDeviceNameConflict):
                update_virtual_device(
                    hass=hass,
                    device=device,
                    existing_virtual_devices=[device],
                    name="Neuer Name",
                )


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
            unit="W",
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
            unit="W",
        ),
        VirtualEntity(
            id="virtual_beleuchtung_power_1",
            device_class="power",
            aggregation="avg",
            unit="W",
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
            unit="W",
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
        "power",
        aggregation,
        "W",
    )


def test_validate_virtual_entity_rejects_unsupported_aggregation() -> None:
    """Reject unsupported aggregation modes."""
    with pytest.raises(
        ValueError,
        match="Unsupported aggregation",
    ):
        validate_virtual_entity(
            "power",
            "median",
            "W",
        )


def test_validate_virtual_entity_rejects_empty_device_class() -> None:
    """Reject an empty device class."""
    with pytest.raises(
        ValueError,
        match="Device class must not be empty",
    ):
        validate_virtual_entity(
            "",
            "sum",
            "W",
        )


def test_validate_virtual_entity_rejects_empty_unit() -> None:
    """Reject an empty unit."""
    with pytest.raises(
        ValueError,
        match="Unit must not be empty",
    ):
        validate_virtual_entity(
            "power",
            "sum",
            "",
        )


def test_create_virtual_entity_uses_base_id() -> None:
    """Use the base ID for the first entity of a device."""
    device = VirtualDevice(
        id="virtual_beleuchtung",
        label_ref="beleuchtung",
        name="Beleuchtung",
    )

    entity = create_virtual_entity(
        device=device,
        device_class="power",
        aggregation="sum",
        unit="W",
    )

    assert entity.id == (
        "virtual_beleuchtung_power"
    )
    assert entity.device_class == "power"
    assert entity.aggregation == "sum"
    assert entity.unit == "W"
    assert entity.name == "power"


def test_create_virtual_entity_uses_suffix() -> None:
    """Use a numeric suffix for a second entity."""
    device = VirtualDevice(
        id="virtual_beleuchtung",
        label_ref="beleuchtung",
        name="Beleuchtung",
        entities=[
            VirtualEntity(
                id="virtual_beleuchtung_power",
                device_class="power",
                aggregation="sum",
                unit="W",
            ),
        ],
    )

    entity = create_virtual_entity(
        device=device,
        device_class="power",
        aggregation="avg",
        unit="W",
    )

    assert entity.id == (
        "virtual_beleuchtung_power_1"
    )


def test_create_virtual_entity_uses_base_id_for_different_class() -> None:
    """Use a separate base ID for another device class."""
    device = VirtualDevice(
        id="virtual_beleuchtung",
        label_ref="beleuchtung",
        name="Beleuchtung",
        entities=[
            VirtualEntity(
                id="virtual_beleuchtung_power",
                device_class="power",
                aggregation="sum",
                unit="W",
            ),
        ],
    )

    entity = create_virtual_entity(
        device=device,
        device_class="energy",
        aggregation="sum",
        unit="kWh",
    )

    assert entity.id == (
        "virtual_beleuchtung_energy"
    )


def test_create_virtual_entity_uses_next_free_suffix() -> None:
    """Use the next available numeric suffix."""
    device = VirtualDevice(
        id="virtual_beleuchtung",
        label_ref="beleuchtung",
        name="Beleuchtung",
        entities=[
            VirtualEntity(
                id="virtual_beleuchtung_power",
                device_class="power",
                aggregation="sum",
                unit="W",
            ),
            VirtualEntity(
                id="virtual_beleuchtung_power_1",
                device_class="power",
                aggregation="avg",
                unit="W",
            ),
        ],
    )

    entity = create_virtual_entity(
        device=device,
        device_class="power",
        aggregation="max",
        unit="W",
    )

    assert entity.id == (
        "virtual_beleuchtung_power_2"
    )


def test_create_virtual_entity_keeps_explicit_name() -> None:
    """Keep an explicitly provided entity name."""
    device = VirtualDevice(
        id="virtual_beleuchtung",
        label_ref="beleuchtung",
        name="Beleuchtung",
    )

    entity = create_virtual_entity(
        device=device,
        device_class="power",
        aggregation="sum",
        unit="W",
        name="Gesamtleistung",
    )

    assert entity.name == "Gesamtleistung"


def test_create_virtual_entity_does_not_modify_device() -> None:
    """Creating an entity does not modify the device."""
    device = VirtualDevice(
        id="virtual_beleuchtung",
        label_ref="beleuchtung",
        name="Beleuchtung",
    )

    entity = create_virtual_entity(
        device=device,
        device_class="power",
        aggregation="sum",
        unit="W",
    )

    assert entity not in device.entities
    assert device.entities == []


def test_add_virtual_entity_adds_entity() -> None:
    """Add a new virtual entity to the device."""
    device = VirtualDevice(
        id="virtual_beleuchtung",
        label_ref="beleuchtung",
        name="Beleuchtung",
    )

    updated = add_virtual_entity(
        device=device,
        device_class="power",
        aggregation="sum",
        unit="W",
    )

    assert len(updated.entities) == 1
    assert updated.entities[0].id == (
        "virtual_beleuchtung_power"
    )


def test_add_virtual_entity_keeps_existing_entities() -> None:
    """Keep existing entities when adding a new one."""
    existing = VirtualEntity(
        id="virtual_beleuchtung_power",
        device_class="power",
        aggregation="sum",
        unit="W",
    )

    device = VirtualDevice(
        id="virtual_beleuchtung",
        label_ref="beleuchtung",
        name="Beleuchtung",
        entities=[existing],
    )

    updated = add_virtual_entity(
        device=device,
        device_class="energy",
        aggregation="sum",
        unit="kWh",
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
        name="Beleuchtung",
    )

    updated = add_virtual_entity(
        device=device,
        device_class="power",
        aggregation="sum",
        unit="W",
    )

    assert device.entities == []
    assert len(updated.entities) == 1
    assert updated is not device


def test_update_virtual_entity_changes_values() -> None:
    """Update the configuration of an existing entity."""
    entity = VirtualEntity(
        id="virtual_beleuchtung_power",
        device_class="power",
        aggregation="sum",
        unit="W",
        name="Gesamtleistung",
    )

    device = VirtualDevice(
        id="virtual_beleuchtung",
        label_ref="beleuchtung",
        name="Beleuchtung",
        entities=[entity],
    )

    updated = update_virtual_entity(
        device=device,
        entity_id="virtual_beleuchtung_power",
        aggregation="avg",
        name="Durchschnittsleistung",
    )

    updated_entity = updated.entities[0]

    assert updated_entity.id == (
        "virtual_beleuchtung_power"
    )
    assert updated_entity.device_class == "power"
    assert updated_entity.aggregation == "avg"
    assert updated_entity.unit == "W"
    assert updated_entity.name == "Durchschnittsleistung"


def test_update_virtual_entity_keeps_id() -> None:
    """Keep the entity ID when updating an entity."""
    entity = VirtualEntity(
        id="virtual_beleuchtung_power_1",
        device_class="power",
        aggregation="sum",
        unit="W",
    )

    device = VirtualDevice(
        id="virtual_beleuchtung",
        label_ref="beleuchtung",
        name="Beleuchtung",
        entities=[entity],
    )

    updated = update_virtual_entity(
        device=device,
        entity_id="virtual_beleuchtung_power_1",
        device_class="power",
        aggregation="max",
        unit="kW",
    )

    assert updated.entities[0].id == (
        "virtual_beleuchtung_power_1"
    )


def test_update_virtual_entity_keeps_unspecified_values() -> None:
    """Keep values that were not explicitly changed."""
    entity = VirtualEntity(
        id="virtual_beleuchtung_power",
        device_class="power",
        aggregation="sum",
        unit="W",
        name="Gesamtleistung",
    )

    device = VirtualDevice(
        id="virtual_beleuchtung",
        label_ref="beleuchtung",
        name="Beleuchtung",
        entities=[entity],
    )

    updated = update_virtual_entity(
        device=device,
        entity_id="virtual_beleuchtung_power",
        name="Neue Leistung",
    )

    updated_entity = updated.entities[0]

    assert updated_entity.device_class == "power"
    assert updated_entity.aggregation == "sum"
    assert updated_entity.unit == "W"
    assert updated_entity.name == "Neue Leistung"


def test_update_virtual_entity_rejects_unknown_entity() -> None:
    """Reject an unknown entity ID."""
    device = VirtualDevice(
        id="virtual_beleuchtung",
        label_ref="beleuchtung",
        name="Beleuchtung",
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
        unit="W",
    )

    device = VirtualDevice(
        id="virtual_beleuchtung",
        label_ref="beleuchtung",
        name="Beleuchtung",
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


def test_update_virtual_entity_does_not_modify_original() -> None:
    """Do not modify the original device."""
    entity = VirtualEntity(
        id="virtual_beleuchtung_power",
        device_class="power",
        aggregation="sum",
        unit="W",
        name="Alt",
    )

    device = VirtualDevice(
        id="virtual_beleuchtung",
        label_ref="beleuchtung",
        name="Beleuchtung",
        entities=[entity],
    )

    updated = update_virtual_entity(
        device=device,
        entity_id="virtual_beleuchtung_power",
        name="Neu",
    )

    assert device.entities[0].name == "Alt"
    assert updated.entities[0].name == "Neu"
    assert updated is not device


def test_delete_virtual_entity_removes_entity() -> None:
    """Remove an existing virtual entity."""
    entity = VirtualEntity(
        id="virtual_beleuchtung_power",
        device_class="power",
        aggregation="sum",
        unit="W",
    )

    device = VirtualDevice(
        id="virtual_beleuchtung",
        label_ref="beleuchtung",
        name="Beleuchtung",
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
        unit="W",
    )

    energy = VirtualEntity(
        id="virtual_beleuchtung_energy",
        device_class="energy",
        aggregation="sum",
        unit="kWh",
    )

    device = VirtualDevice(
        id="virtual_beleuchtung",
        label_ref="beleuchtung",
        name="Beleuchtung",
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
        name="Beleuchtung",
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
        unit="W",
    )

    device = VirtualDevice(
        id="virtual_beleuchtung",
        label_ref="beleuchtung",
        name="Beleuchtung",
        entities=[entity],
    )

    updated = delete_virtual_entity(
        device,
        "virtual_beleuchtung_power",
    )

    assert device.entities == [entity]
    assert updated.entities == []
    assert updated is not device

