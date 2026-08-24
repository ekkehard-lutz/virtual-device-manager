"""Home Assistant Recorder-backed historical data reader."""

from __future__ import annotations

from datetime import datetime
from functools import partial
from typing import Any

from homeassistant.components.recorder import history, statistics
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.recorder import get_instance
from homeassistant.util import dt as dt_util

from .models import HistoryResolution, RawSourceEvent, StatisticsSlot

STATISTIC_FIELDS = {"mean", "min", "max", "state", "sum", "last_reset"}


class HistoricalDataProvider:
    """Read and normalize history without applying VDM aggregation rules."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass

    async def async_read_raw(
        self,
        entity_ids: tuple[str, ...],
        start: datetime,
        end: datetime,
    ) -> tuple[RawSourceEvent, ...]:
        """Read raw states, including the state active at the chunk start."""
        if not entity_ids:
            return ()

        recorder = get_instance(self._hass)
        result = await recorder.async_add_executor_job(
            history.get_significant_states,
            self._hass,
            start,
            end,
            list(entity_ids),
            None,
            True,
            False,
            False,
            False,
        )
        return self._normalize_raw(result)

    async def async_read_statistics(
        self,
        resolution: HistoryResolution,
        entity_ids: tuple[str, ...],
        start: datetime,
        end: datetime,
    ) -> tuple[StatisticsSlot, ...]:
        """Read aligned five-minute or hourly source statistics."""
        if resolution not in (HistoryResolution.FIVE_MINUTE, HistoryResolution.HOUR):
            raise ValueError(f"Unsupported statistics resolution: {resolution}")
        if not entity_ids:
            return ()

        recorder = get_instance(self._hass)
        metadata = await recorder.async_add_executor_job(
            partial(
                statistics.get_metadata,
                self._hass,
                statistic_ids=set(entity_ids),
            )
        )
        result = await recorder.async_add_executor_job(
            statistics.statistics_during_period,
            self._hass,
            start,
            end,
            set(entity_ids),
            resolution.value,
            None,
            STATISTIC_FIELDS,
        )
        return self._normalize_statistics(result, metadata)

    @staticmethod
    def _normalize_raw(
        result: dict[str, list[State | dict[str, Any]]],
    ) -> tuple[RawSourceEvent, ...]:
        events: list[RawSourceEvent] = []
        for entity_id, states in result.items():
            for state in states:
                if isinstance(state, State):
                    state_value = state.state
                    timestamp = state.last_updated
                    unit = state.attributes.get("unit_of_measurement")
                else:
                    state_value = state.get("state", state.get("s"))
                    timestamp = state.get("last_updated", state.get("lu"))
                    unit = state.get("attributes", {}).get("unit_of_measurement")
                try:
                    value = float(state_value)
                except (TypeError, ValueError):
                    value = None
                if not isinstance(timestamp, datetime):
                    continue
                events.append(RawSourceEvent(entity_id, timestamp, value, unit))
        return tuple(
            sorted(events, key=lambda event: (event.timestamp, event.entity_id))
        )

    @staticmethod
    def _normalize_statistics(
        result: dict[str, list[dict[str, Any]]],
        metadata: dict[str, tuple[int, dict[str, Any]]],
    ) -> tuple[StatisticsSlot, ...]:
        slots: list[StatisticsSlot] = []
        for entity_id, rows in result.items():
            entity_metadata = metadata.get(entity_id)
            unit = (
                entity_metadata[1].get("unit_of_measurement")
                if entity_metadata
                else None
            )
            for row in rows:
                start = row["start"]
                if not isinstance(start, datetime):
                    start = dt_util.utc_from_timestamp(start)
                last_reset = row.get("last_reset")
                if last_reset is not None and not isinstance(last_reset, datetime):
                    last_reset = dt_util.utc_from_timestamp(last_reset)
                slots.append(
                    StatisticsSlot(
                        entity_id=entity_id,
                        start=start,
                        unit=unit,
                        mean=row.get("mean"),
                        minimum=row.get("min"),
                        maximum=row.get("max"),
                        state=row.get("state"),
                        sum=row.get("sum"),
                        last_reset=last_reset,
                    )
                )
        return tuple(sorted(slots, key=lambda slot: (slot.start, slot.entity_id)))
