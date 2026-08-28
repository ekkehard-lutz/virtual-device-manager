"""Persistent storage for the Virtual Device Manager integration."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import STORAGE_KEY, STORAGE_VERSION
from .models import FilterCondition, SourceFilter, VirtualDevice, VirtualEntity


def _filter_to_dict(source_filter: SourceFilter) -> dict[str, Any]:
    return {
        "mode": source_filter.mode,
        "conditions": [
            {"field": item.field, "operator": item.operator, "value": item.value}
            for item in source_filter.conditions
        ],
    }


def _filter_from_dict(data: Any, default_mode: str) -> SourceFilter:
    data = data if isinstance(data, dict) else {}
    return SourceFilter(
        mode=data.get("mode", default_mode),
        conditions=[FilterCondition(**item) for item in data.get("conditions", [])],
    )


def _virtual_entity_to_dict(
    entity: VirtualEntity,
) -> dict[str, Any]:
    """Convert a VirtualEntity to storage data."""
    return {
        "device_class": entity.device_class,
        "aggregation": entity.aggregation,
        "include_filter": _filter_to_dict(entity.include_filter),
        "exclude_filter": _filter_to_dict(entity.exclude_filter),
    }


def _virtual_entity_from_dict(
    entity_id: str,
    data: dict[str, Any],
) -> VirtualEntity:
    """Create a VirtualEntity from storage data."""
    return VirtualEntity(
        id=entity_id,
        device_class=data["device_class"],
        aggregation=data["aggregation"],
        include_filter=_filter_from_dict(data.get("include_filter"), "all"),
        exclude_filter=_filter_from_dict(data.get("exclude_filter"), "any"),
    )


def _virtual_device_to_dict(
    device: VirtualDevice,
) -> dict[str, Any]:
    """Convert a VirtualDevice to storage data."""
    return {
        "label_ref": device.label_ref,
        "entities": {
            entity.id: _virtual_entity_to_dict(entity) for entity in device.entities
        },
    }


def _virtual_device_from_dict(
    device_id: str,
    data: dict[str, Any],
) -> VirtualDevice:
    """Create a VirtualDevice from storage data."""
    entities = [
        _virtual_entity_from_dict(
            entity_id,
            entity_data,
        )
        for entity_id, entity_data in data.get("entities", {}).items()
    ]

    return VirtualDevice(
        id=device_id,
        label_ref=data.get("label_ref", ""),
        entities=entities,
    )


class VirtualDeviceStorage:
    """Persistent storage for Virtual Device Manager state."""

    def __init__(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Initialize the storage."""
        self.hass = hass

        self._store = Store[dict[str, Any]](
            hass,
            STORAGE_VERSION,
            STORAGE_KEY,
        )

        self._data: dict[str, Any] = {
            "version": STORAGE_VERSION,
            "virtual_devices": {},
        }

    async def async_load(self) -> None:
        """Load stored data from Home Assistant."""
        data = await self._store.async_load()

        if not data:
            return

        self._data = {
            "version": STORAGE_VERSION,
            "virtual_devices": data.get(
                "virtual_devices",
                {},
            ),
        }

    async def async_save(self) -> None:
        """Save current data to Home Assistant."""
        await self._store.async_save(self._data)

    def get_virtual_devices(self) -> list[VirtualDevice]:
        """Return all virtual devices."""
        return [
            _virtual_device_from_dict(
                device_id,
                data,
            )
            for device_id, data in self._data["virtual_devices"].items()
        ]

    def get_virtual_device(
        self,
        device_id: str,
    ) -> VirtualDevice | None:
        """Return one virtual device."""
        data = self._data["virtual_devices"].get(
            device_id,
        )

        if data is None:
            return None

        return _virtual_device_from_dict(
            device_id,
            data,
        )

    async def async_save_virtual_device(
        self,
        device: VirtualDevice,
    ) -> None:
        """Create or update a virtual device."""
        self._data["virtual_devices"][device.id] = _virtual_device_to_dict(device)

        await self.async_save()

    async def async_delete_virtual_device(
        self,
        device_id: str,
    ) -> None:
        """Delete a virtual device."""
        self._data["virtual_devices"].pop(
            device_id,
            None,
        )

        await self.async_save()
