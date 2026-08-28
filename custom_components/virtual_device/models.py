"""Data models for the Virtual Device Manager integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class FilterCondition:
    """One source metadata condition."""

    field: str
    operator: str
    value: Any = None


@dataclass(slots=True)
class SourceFilter:
    """A group of source metadata conditions."""

    mode: str
    conditions: list[FilterCondition] = field(default_factory=list)


@dataclass(slots=True)
class VirtualEntity:
    """Configuration for one virtual entity."""

    id: str
    device_class: str
    aggregation: str
    include_filter: SourceFilter = field(
        default_factory=lambda: SourceFilter(mode="all")
    )
    exclude_filter: SourceFilter = field(
        default_factory=lambda: SourceFilter(mode="any")
    )


@dataclass(slots=True)
class VirtualDevice:
    """Configuration for one virtual device."""

    id: str
    label_ref: str
    entities: list[VirtualEntity] = field(default_factory=list)
