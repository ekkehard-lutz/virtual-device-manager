"""Tests for integration and panel translations."""

from __future__ import annotations

import json
from pathlib import Path

from custom_components.virtual_device.sensor import VirtualDeviceSensor
from custom_components.virtual_device.translation import (
    normalize_language,
    panel_translations,
)
from tests.test_sensor import _create_sensor

TRANSLATIONS = Path("custom_components/virtual_device/translations")
DEVICE_CLASSES = {"energy", "power", "temperature", "voltage", "current"}
AGGREGATIONS = {"sum", "avg", "min", "max", "median"}
ENTITY_NAMES = {
    "en": {
        "energy": "Energy",
        "power": "Power",
        "temperature": "Temperature",
        "voltage": "Voltage",
        "current": "Current",
    },
    "de": {
        "energy": "Energie",
        "power": "Leistung",
        "temperature": "Temperatur",
        "voltage": "Spannung",
        "current": "Strom",
    },
}


def _keys(value: dict, prefix: str = "") -> set[str]:
    """Return recursive leaf keys from a translation resource."""
    result = set()
    for key, child in value.items():
        path = f"{prefix}.{key}" if prefix else key
        result.update(_keys(child, path) if isinstance(child, dict) else {path})
    return result


def test_translation_resources_have_identical_complete_structure() -> None:
    """Validate JSON resources and German coverage of all English keys."""
    resources = {
        language: json.loads((TRANSLATIONS / f"{language}.json").read_text("utf-8"))
        for language in ("en", "de")
    }
    assert _keys(resources["en"]) == _keys(resources["de"])
    for language, resource in resources.items():
        assert set(resource["panel"]["device_classes"]) == DEVICE_CLASSES
        assert set(resource["panel"]["aggregations"]) == AGGREGATIONS
        assert set(resource["entity"]["sensor"]) == DEVICE_CLASSES
        assert resource["panel"]["device_classes"] == ENTITY_NAMES[language]
        assert {
            device_class: data["name"]
            for device_class, data in resource["entity"]["sensor"].items()
        } == ENTITY_NAMES[language]


def test_language_normalization_and_english_fallback() -> None:
    """Normalize HA variants and fall back to English for unsupported languages."""
    available = {"en", "de"}
    assert normalize_language("de-AT", available) == "de"
    assert normalize_language("en_GB", available) == "en"
    assert normalize_language("fr", available) == "en"
    result = panel_translations(
        {"en": {"panel": {"message": "English"}}, "de": {"panel": {}}},
        "de-DE",
    )
    assert result == {"language": "de", "messages": {"message": "English"}}


def test_virtual_sensor_translation_metadata_preserves_identity() -> None:
    """Use HA translations without changing stable entity identity."""
    original = _create_sensor()
    sensor = VirtualDeviceSensor(original._device, original._virtual_entity)
    assert sensor.translation_key == "power"
    assert sensor.name is None
    assert sensor.unique_id == "virtual_device_virtual_beleuchtung_power"
    assert sensor._virtual_entity.id == "virtual_beleuchtung_power"
