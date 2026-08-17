"""Data models for the Virtual Device Manager integration."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class VirtualEntity:
    """Configuration for one virtual entity."""

    id: str
    device_class: str
    aggregation: str
    unit: str
    name: str | None = None

    def __post_init__(self) -> None:
        """Apply default values."""
        if not self.name:
            self.name = self.device_class


@dataclass(slots=True)
class VirtualDevice:
    """Configuration for one virtual device."""

    id: str
    label_ref: str
    name: str | None = None
    entities: list[VirtualEntity] = field(default_factory=list)
