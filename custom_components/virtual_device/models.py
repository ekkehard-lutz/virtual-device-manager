"""Data models for the Virtual Device Manager integration."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class VirtualEntity:
    """Configuration for one virtual entity."""

    id: str
    device_class: str
    aggregation: str


@dataclass(slots=True)
class VirtualDevice:
    """Configuration for one virtual device."""

    id: str
    label_ref: str
    entities: list[VirtualEntity] = field(default_factory=list)
