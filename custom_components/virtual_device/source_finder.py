"""Find source entities for virtual entities."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .aggregator import SourceValue


def get_entities_for_label(
    hass: HomeAssistant,
    label_ref: str,
) -> list[str]:
    """Return all entities having the requested label."""
    entity_registry = er.async_get(hass)

    entities = getattr(entity_registry, "entities", None)

    if entities is not None:
        if hasattr(entities, "values"):
            entries = entities.values()
        else:
            entries = entities

        return sorted(
            entity.entity_id for entity in entries if label_ref in entity.labels
        )

    return sorted(
        entity_id
        for entity_id in (state.entity_id for state in hass.states.async_all())
        if (entity := entity_registry.async_get(entity_id)) is not None
        and label_ref in entity.labels
    )


def get_sensor_entities_for_label(
    hass: HomeAssistant,
    label_ref: str,
) -> list[str]:
    """Return sensor entities having the requested label."""
    return [
        entity_id
        for entity_id in get_entities_for_label(hass, label_ref)
        if entity_id.startswith("sensor.")
    ]


def get_source_entities(
    hass: HomeAssistant,
    label_ref: str,
    device_class: str,
) -> list[str]:
    """Return sensor entities matching label and device class."""
    source_entities: list[str] = []

    for entity_id in get_sensor_entities_for_label(hass, label_ref):
        state = hass.states.get(entity_id)

        if state is None:
            continue

        if state.attributes.get("device_class") != device_class:
            continue

        source_entities.append(entity_id)

    return source_entities


def get_source_values(
    hass: HomeAssistant,
    label_ref: str,
    device_class: str,
) -> list[SourceValue]:
    """Return numeric source values matching label and device class."""
    source_values: list[SourceValue] = []

    for entity_id in get_source_entities(
        hass,
        label_ref,
        device_class,
    ):
        state = hass.states.get(entity_id)

        if state is None:
            continue

        if state.state in ("unknown", "unavailable"):
            continue

        try:
            value = float(state.state)
        except (TypeError, ValueError):
            continue

        unit = state.attributes.get("unit_of_measurement")

        if not unit:
            continue

        source_values.append(
            SourceValue(
                entity_id=entity_id,
                value=value,
                unit=unit,
            )
        )

    return source_values
