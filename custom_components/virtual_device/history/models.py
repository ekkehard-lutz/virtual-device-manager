"""Recorder-neutral history synchronization models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class HistoryResolution(StrEnum):
    """Historical resolutions understood by the calculation engine."""

    RAW = "raw"
    FIVE_MINUTE = "5minute"
    HOUR = "hour"


class SyncStatus(StrEnum):
    """Status of a history synchronization or one virtual entity."""

    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partially_successful"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class VirtualEntitySourceSnapshot:
    """Immutable current source assignment for one virtual entity."""

    virtual_entity_id: str
    device_class: str
    aggregation: str
    source_entity_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SourceSnapshot:
    """Immutable current source assignment for a virtual device."""

    device_id: str
    entities: tuple[VirtualEntitySourceSnapshot, ...]
    created_at: datetime


@dataclass(frozen=True, slots=True)
class RawSourceEvent:
    """One source state transition normalized from Recorder history."""

    entity_id: str
    timestamp: datetime
    value: float | None
    unit: str | None


@dataclass(frozen=True, slots=True)
class RawVirtualPoint:
    """One reconstructed virtual raw-history point."""

    timestamp: datetime
    value: float


@dataclass(frozen=True, slots=True)
class StatisticsSlot:
    """One source or virtual statistics slot."""

    entity_id: str
    start: datetime
    unit: str | None
    mean: float | None = None
    minimum: float | None = None
    maximum: float | None = None
    state: float | None = None
    sum: float | None = None
    last_reset: datetime | None = None

    def has_numeric_data(self) -> bool:
        """Return whether this slot contains a usable numeric field."""
        return any(
            value is not None
            for value in (self.mean, self.minimum, self.maximum, self.state, self.sum)
        )


@dataclass(frozen=True, slots=True)
class VirtualHistoryResult:
    """Prepared neutral history for one virtual entity."""

    virtual_entity_id: str
    raw: tuple[RawVirtualPoint, ...] = ()
    five_minute: tuple[StatisticsSlot, ...] = ()
    hourly: tuple[StatisticsSlot, ...] = ()


@dataclass(frozen=True, slots=True)
class VirtualEntitySyncResult:
    """Synchronization result for one virtual entity."""

    virtual_entity_id: str
    status: SyncStatus
    reason: str | None = None
    reason_code: str | None = None
    range_start: datetime | None = None
    range_end: datetime | None = None
    resolutions: tuple[HistoryResolution, ...] = ()
    hourly_slots_upserted: int = 0


@dataclass(frozen=True, slots=True)
class HistorySyncResult:
    """Synchronization result for a virtual device."""

    device_id: str
    status: SyncStatus
    entities: tuple[VirtualEntitySyncResult, ...]
    started_at: datetime
    completed_at: datetime
    persistence_mode: str = "hourly_upsert"
    limitations: tuple[str, ...] = field(
        default=(
            "Raw history and 5-minute statistics are calculated but not persisted.",
            "Hourly upserts cannot remove obsolete slots absent from a recalculation.",
        )
    )
