"""Tests for Virtual Device Manager source finding."""

from unittest.mock import MagicMock

from custom_components.virtual_device.aggregator import SourceValue
from custom_components.virtual_device.source_finder import (
    get_entities_for_label,
    get_sensor_entities_for_label,
    get_source_entities,
    get_source_values,
)


def test_get_entities_for_label(monkeypatch) -> None:
    """Return all entities having the requested label."""
    hass = MagicMock()

    entity_registry = MagicMock()
    entity_registry.entities = {
        "sensor.power_1": MagicMock(
            entity_id="sensor.power_1",
            labels={"label-id-energie"},
        ),
        "sensor.power_2": MagicMock(
            entity_id="sensor.power_2",
            labels={"label-id-energie", "label-id-beleuchtung"},
        ),
        "sensor.temperature": MagicMock(
            entity_id="sensor.temperature",
            labels={"label-id-temperatur"},
        ),
        "light.test": MagicMock(
            entity_id="light.test",
            labels={"label-id-energie"},
        ),
    }

    from custom_components.virtual_device import source_finder

    monkeypatch.setattr(
        source_finder.er,
        "async_get",
        lambda hass: entity_registry,
    )

    result = get_entities_for_label(
        hass,
        "label-id-energie",
    )

    assert result == [
        "light.test",
        "sensor.power_1",
        "sensor.power_2",
    ]


def test_get_sensor_entities_for_label(monkeypatch) -> None:
    """Return only sensor entities having the requested label."""
    hass = MagicMock()

    entity_registry = MagicMock()
    entity_registry.entities = {
        "sensor.power_1": MagicMock(
            entity_id="sensor.power_1",
            labels={"label-id-energie"},
        ),
        "sensor.power_2": MagicMock(
            entity_id="sensor.power_2",
            labels={"label-id-energie", "label-id-beleuchtung"},
        ),
        "sensor.temperature": MagicMock(
            entity_id="sensor.temperature",
            labels={"label-id-temperatur"},
        ),
        "light.test": MagicMock(
            entity_id="light.test",
            labels={"label-id-energie"},
        ),
        "switch.test": MagicMock(
            entity_id="switch.test",
            labels={"label-id-energie"},
        ),
    }

    from custom_components.virtual_device import source_finder

    monkeypatch.setattr(
        source_finder.er,
        "async_get",
        lambda hass: entity_registry,
    )

    result = get_sensor_entities_for_label(
        hass,
        "label-id-energie",
    )

    assert result == [
        "sensor.power_1",
        "sensor.power_2",
    ]


def test_get_source_entities_by_device_class(monkeypatch) -> None:
    """Return sensor entities matching label and device class."""
    hass = MagicMock()

    entity_registry = MagicMock()
    entity_registry.entities = {
        "sensor.power_1": MagicMock(
            entity_id="sensor.power_1",
            labels={"label-id-energie"},
        ),
        "sensor.power_2": MagicMock(
            entity_id="sensor.power_2",
            labels={"label-id-energie"},
        ),
        "sensor.energy": MagicMock(
            entity_id="sensor.energy",
            labels={"label-id-energie"},
        ),
        "sensor.temperature": MagicMock(
            entity_id="sensor.temperature",
            labels={"label-id-energie"},
        ),
    }

    states = {
        "sensor.power_1": MagicMock(
            attributes={"device_class": "power"},
        ),
        "sensor.power_2": MagicMock(
            attributes={"device_class": "power"},
        ),
        "sensor.energy": MagicMock(
            attributes={"device_class": "energy"},
        ),
        "sensor.temperature": MagicMock(
            attributes={"device_class": "temperature"},
        ),
    }

    hass.states.get.side_effect = states.get

    from custom_components.virtual_device import source_finder

    monkeypatch.setattr(
        source_finder.er,
        "async_get",
        lambda hass: entity_registry,
    )

    result = get_source_entities(
        hass,
        "label-id-energie",
        "power",
    )

    assert result == [
        "sensor.power_1",
        "sensor.power_2",
    ]


def test_get_source_values(monkeypatch) -> None:
    """Return numeric source values with their units."""
    hass = MagicMock()

    entity_registry = MagicMock()
    entity_registry.entities = {
        "sensor.power_1": MagicMock(
            entity_id="sensor.power_1",
            labels={"label-id-energie"},
        ),
        "sensor.power_2": MagicMock(
            entity_id="sensor.power_2",
            labels={"label-id-energie"},
        ),
        "sensor.unknown": MagicMock(
            entity_id="sensor.unknown",
            labels={"label-id-energie"},
        ),
        "sensor.unavailable": MagicMock(
            entity_id="sensor.unavailable",
            labels={"label-id-energie"},
        ),
    }

    states = {
        "sensor.power_1": MagicMock(
            state="4200",
            attributes={
                "device_class": "power",
                "unit_of_measurement": "W",
            },
        ),
        "sensor.power_2": MagicMock(
            state="1.5",
            attributes={
                "device_class": "power",
                "unit_of_measurement": "kW",
            },
        ),
        "sensor.unknown": MagicMock(
            state="unknown",
            attributes={
                "device_class": "power",
                "unit_of_measurement": "W",
            },
        ),
        "sensor.unavailable": MagicMock(
            state="unavailable",
            attributes={
                "device_class": "power",
                "unit_of_measurement": "W",
            },
        ),
    }

    hass.states.get.side_effect = states.get

    from custom_components.virtual_device import source_finder

    monkeypatch.setattr(
        source_finder.er,
        "async_get",
        lambda hass: entity_registry,
    )

    result = get_source_values(
        hass,
        "label-id-energie",
        "power",
    )

    assert result == [
        SourceValue(
            entity_id="sensor.power_1",
            value=4200.0,
            unit="W",
        ),
        SourceValue(
            entity_id="sensor.power_2",
            value=1.5,
            unit="kW",
        ),
    ]
