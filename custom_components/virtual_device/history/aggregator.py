"""Recorder-independent historical aggregation."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime

from ..aggregator import SourceValue, aggregate_values
from .models import RawSourceEvent, RawVirtualPoint, StatisticsSlot


@dataclass(slots=True)
class RawTimelineState:
    """Minimal source state carried between raw-history chunks."""

    values: dict[str, SourceValue] = field(default_factory=dict)
    last_emitted_timestamp: datetime | None = None


class HistoricalAggregator:
    """Apply normal VDM aggregation semantics at each history resolution."""

    def aggregate_raw(
        self,
        events: Iterable[RawSourceEvent],
        device_class: str,
        aggregation: str,
        state: RawTimelineState | None = None,
    ) -> tuple[tuple[RawVirtualPoint, ...], RawTimelineState]:
        """Merge source events by timestamp and aggregate current valid values."""
        state = state or RawTimelineState()
        by_timestamp: dict[datetime, list[RawSourceEvent]] = defaultdict(list)
        for event in events:
            by_timestamp[event.timestamp].append(event)

        points: list[RawVirtualPoint] = []
        for timestamp in sorted(by_timestamp):
            for event in sorted(
                by_timestamp[timestamp], key=lambda item: item.entity_id
            ):
                if event.value is None or not event.unit:
                    state.values.pop(event.entity_id, None)
                else:
                    state.values[event.entity_id] = SourceValue(
                        entity_id=event.entity_id,
                        value=event.value,
                        unit=event.unit,
                    )
            value = aggregate_values(
                list(state.values.values()), device_class, aggregation
            )
            if value is not None and timestamp != state.last_emitted_timestamp:
                points.append(RawVirtualPoint(timestamp=timestamp, value=value))
                state.last_emitted_timestamp = timestamp
        return tuple(points), state

    def aggregate_statistics(
        self,
        slots: Iterable[StatisticsSlot],
        virtual_entity_id: str,
        device_class: str,
        aggregation: str,
        completed_before: datetime,
    ) -> tuple[StatisticsSlot, ...]:
        """Aggregate source statistic fields independently per aligned slot."""
        by_start: dict[datetime, list[StatisticsSlot]] = defaultdict(list)
        for slot in slots:
            if slot.start < completed_before:
                by_start[slot.start].append(slot)

        result: list[StatisticsSlot] = []
        for start in sorted(by_start):
            source_slots = by_start[start]
            fields = {
                field_name: self._aggregate_statistic_field(
                    source_slots, field_name, device_class, aggregation
                )
                for field_name in ("mean", "minimum", "maximum", "state", "sum")
            }
            if all(value is None for value in fields.values()):
                continue
            resets = {
                slot.last_reset for slot in source_slots if slot.last_reset is not None
            }
            result.append(
                StatisticsSlot(
                    entity_id=virtual_entity_id,
                    start=start,
                    unit=self._native_unit(device_class),
                    last_reset=next(iter(resets)) if len(resets) == 1 else None,
                    **fields,
                )
            )
        return tuple(result)

    @staticmethod
    def _aggregate_statistic_field(
        slots: list[StatisticsSlot],
        field_name: str,
        device_class: str,
        aggregation: str,
    ) -> float | None:
        values = [
            SourceValue(slot.entity_id, value, slot.unit)
            for slot in slots
            if (value := getattr(slot, field_name)) is not None and slot.unit
        ]
        return aggregate_values(values, device_class, aggregation)

    @staticmethod
    def _native_unit(device_class: str) -> str:
        from ..device_class_metadata import get_device_class_metadata

        return get_device_class_metadata(device_class).native_unit
