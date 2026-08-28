"""Tests for generic source metadata filters."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from custom_components.virtual_device.models import FilterCondition, SourceFilter
from custom_components.virtual_device.source_filter import (
    MISSING,
    evaluate_operator,
    filter_source_entities,
    resolve_condition_value,
    validate_condition,
    validate_filter,
)
from custom_components.virtual_device.storage import (
    _virtual_entity_from_dict,
    _virtual_entity_to_dict,
)


def test_v1_entity_loads_with_backward_compatible_defaults() -> None:
    entity = _virtual_entity_from_dict(
        "old", {"device_class": "temperature", "aggregation": "avg"}
    )
    assert entity.include_filter == SourceFilter("all")
    assert entity.exclude_filter == SourceFilter("any")


def test_only_filter_configuration_is_persisted() -> None:
    entity = _virtual_entity_from_dict(
        "old", {"device_class": "temperature", "aggregation": "avg"}
    )
    assert _virtual_entity_to_dict(entity)["include_filter"] == {
        "mode": "all",
        "conditions": [],
    }


@pytest.mark.parametrize(
    ("operator", "actual", "expression", "expected"),
    [
        ("equals", 1, "1", True),
        ("not_equals", True, "false", True),
        ("contains", {"outside", "inside"}, "outside", True),
        ("not_contains", ["a"], "b", True),
        ("starts_with", "temperature:100", "temp", True),
        ("ends_with", "temperature:100", "100", True),
        ("regex", "temperature:100", r"temperature:\d+", True),
        ("is_empty", None, None, True),
        ("is_not_empty", {}, None, False),
    ],
)
def test_operators(operator, actual, expression, expected) -> None:
    assert evaluate_operator(actual, operator, expression) is expected


@pytest.mark.parametrize(
    "field",
    ["foo.name", "entity", "entity..name", "entity.entity-name", "sensor.device_class"],
)
def test_invalid_paths_rejected(field) -> None:
    with pytest.raises(ValueError):
        validate_condition(FilterCondition(field, "equals", "x"))


def test_future_attribute_is_valid_but_invalid_regex_is_not() -> None:
    validate_condition(FilterCondition("entity.some_future_attribute", "equals", "x"))
    with pytest.raises(ValueError):
        validate_condition(FilterCondition("entity.unique_id", "regex", "["))


def test_invalid_mode_and_missing_expression_rejected() -> None:
    with pytest.raises(ValueError):
        validate_filter(SourceFilter("neither"))
    with pytest.raises(ValueError):
        validate_condition(FilterCondition("entity.name", "equals"))


def _hass(monkeypatch):
    entity_entries = {
        "sensor.internal": SimpleNamespace(
            entity_id="sensor.internal",
            entity_category="diagnostic",
            device_id="dev1",
            labels={"inside"},
            options={"sensor": {"suggested_display_precision": 1}},
        ),
        "sensor.external": SimpleNamespace(
            entity_id="sensor.external",
            entity_category=None,
            device_id="dev1",
            labels={"outside"},
            options={},
        ),
    }
    devices = {"dev1": SimpleNamespace(manufacturer="Shelly", model="Plus")}
    states = {
        entity_id: SimpleNamespace(
            state="20",
            attributes={"device_class": "temperature", "friendly_name": entity_id},
        )
        for entity_id in entity_entries
    }
    hass = MagicMock()
    hass.states.get.side_effect = states.get
    entity_registry = MagicMock()
    entity_registry.async_get.side_effect = entity_entries.get
    device_registry = MagicMock()
    device_registry.async_get.side_effect = devices.get
    monkeypatch.setattr(
        "custom_components.virtual_device.source_filter.er.async_get",
        lambda hass: entity_registry,
    )
    monkeypatch.setattr(
        "custom_components.virtual_device.source_filter.dr.async_get",
        lambda hass: device_registry,
    )
    return hass


def test_registry_device_state_and_nested_resolution(monkeypatch) -> None:
    hass = _hass(monkeypatch)
    assert (
        resolve_condition_value(hass, "sensor.internal", "entity.entity_category")
        == "diagnostic"
    )
    assert (
        resolve_condition_value(hass, "sensor.internal", "device.manufacturer")
        == "Shelly"
    )
    assert (
        resolve_condition_value(hass, "sensor.internal", "state.friendly_name")
        == "sensor.internal"
    )
    assert (
        resolve_condition_value(
            hass, "sensor.internal", "state.attributes.device_class"
        )
        == "temperature"
    )
    assert (
        resolve_condition_value(
            hass, "sensor.internal", "entity.options.sensor.suggested_display_precision"
        )
        == 1
    )
    assert (
        resolve_condition_value(hass, "sensor.internal", "entity.entity_cat") is MISSING
    )


def test_real_world_exclude_and_diagnostics(monkeypatch) -> None:
    hass = _hass(monkeypatch)
    result, diagnostics = filter_source_entities(
        hass,
        ["sensor.internal", "sensor.external"],
        SourceFilter("all"),
        SourceFilter(
            "any", [FilterCondition("entity.entity_category", "equals", "diagnostic")]
        ),
    )
    assert result == ["sensor.external"]
    assert diagnostics.base_candidate_count == 2
    assert diagnostics.exclude[0].field_hit is True
    assert diagnostics.exclude[0].rule_hit is True


@pytest.mark.parametrize(
    ("include_mode", "exclude_mode", "expected"),
    [
        ("all", "all", ["sensor.internal"]),
        ("any", "all", ["sensor.internal"]),
        ("all", "any", []),
        ("any", "any", []),
    ],
)
def test_all_any_modes_and_no_short_circuit(
    monkeypatch, include_mode, exclude_mode, expected
) -> None:
    hass = _hass(monkeypatch)
    include = SourceFilter(
        include_mode,
        [
            FilterCondition("device.manufacturer", "equals", "Shelly"),
            FilterCondition("entity.entity_category", "equals", "diagnostic"),
        ],
    )
    exclude = SourceFilter(
        exclude_mode,
        [
            FilterCondition("entity.labels", "contains", "inside"),
            FilterCondition("device.model", "equals", "Wrong"),
        ],
    )
    result, diagnostics = filter_source_entities(
        hass, ["sensor.internal"], include, exclude
    )
    assert result == expected
    assert all(item.field_hit for item in diagnostics.include + diagnostics.exclude)
    assert diagnostics.exclude[1].rule_hit is False


def test_zero_candidates_and_missing_is_not_none(monkeypatch) -> None:
    hass = _hass(monkeypatch)
    condition = FilterCondition("entity.unknown", "is_empty")
    result, diagnostics = filter_source_entities(
        hass, [], SourceFilter("all", [condition]), SourceFilter("any")
    )
    assert result == []
    assert diagnostics.base_candidate_count == 0
    assert diagnostics.include[0].field_hit is False
    result, diagnostics = filter_source_entities(
        hass, ["sensor.external"], SourceFilter("all", [condition]), SourceFilter("any")
    )
    assert result == []
    assert diagnostics.include[0].field_hit is False
    assert diagnostics.include[0].rule_hit is False
