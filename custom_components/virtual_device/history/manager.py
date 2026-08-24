"""Explicit orchestration of VDM history synchronization."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.recorder import get_instance

from ..models import VirtualDevice
from ..source_manager import SourceManager
from .aggregator import HistoricalAggregator, RawTimelineState
from .models import (
    HistoryResolution,
    HistorySyncResult,
    SourceSnapshot,
    SyncStatus,
    VirtualEntitySourceSnapshot,
    VirtualEntitySyncResult,
)
from .persistence import HistoryPersistenceAdapter
from .provider import HistoricalDataProvider

_LOGGER = logging.getLogger(__name__)
HOURLY_HISTORY_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
CHUNK_SIZE = timedelta(days=365)


class HistorySyncBusyError(RuntimeError):
    """Raised when the integration-wide synchronization lock is occupied."""


class HistorySyncManager:
    """Coordinate manually requested history calculations and hourly upserts."""

    def __init__(
        self,
        hass: HomeAssistant,
        source_manager: SourceManager,
        statistic_id_resolver: Callable[[str], str | None],
        provider: HistoricalDataProvider | None = None,
        aggregator: HistoricalAggregator | None = None,
        persistence: HistoryPersistenceAdapter | None = None,
        hourly_history_start: datetime = HOURLY_HISTORY_EPOCH,
    ) -> None:
        self._hass = hass
        self._source_manager = source_manager
        self._resolve_statistic_id = statistic_id_resolver
        self._provider = provider or HistoricalDataProvider(hass)
        self._aggregator = aggregator or HistoricalAggregator()
        self._persistence = persistence or HistoryPersistenceAdapter(hass)
        self._hourly_history_start = hourly_history_start
        self._lock = asyncio.Lock()
        self._status = SyncStatus.IDLE

    @property
    def status(self) -> SyncStatus:
        """Return current global synchronization status."""
        return self._status

    async def async_sync(self, device: VirtualDevice) -> HistorySyncResult:
        """Synchronize one VD only after an explicit caller request."""
        if self._lock.locked():
            raise HistorySyncBusyError("Another history synchronization is running")

        async with self._lock:
            self._status = SyncStatus.RUNNING
            started_at = datetime.now(UTC)
            _LOGGER.info("History sync started for VD %s", device.id)
            try:
                snapshot = await self._async_snapshot(device)
                results = []
                for entity in snapshot.entities:
                    results.append(await self._async_sync_entity(entity, started_at))
                status = self._overall_status(results)
                self._status = status
                completed_at = datetime.now(UTC)
                _LOGGER.info("History sync completed for VD %s: %s", device.id, status)
                return HistorySyncResult(
                    device_id=device.id,
                    status=status,
                    entities=tuple(results),
                    started_at=started_at,
                    completed_at=completed_at,
                )
            except Exception:
                self._status = SyncStatus.FAILED
                raise
            finally:
                if self._status is SyncStatus.RUNNING:
                    self._status = SyncStatus.FAILED

    async def _async_snapshot(self, device: VirtualDevice) -> SourceSnapshot:
        await self._source_manager.async_reconcile(self._hass)
        snapshot = SourceSnapshot(
            device_id=device.id,
            entities=tuple(
                VirtualEntitySourceSnapshot(
                    virtual_entity_id=entity.id,
                    device_class=entity.device_class,
                    aggregation=entity.aggregation,
                    source_entity_ids=tuple(
                        sorted(self._source_manager.get_sources(entity.id))
                    ),
                )
                for entity in device.entities
            ),
            created_at=datetime.now(UTC),
        )
        _LOGGER.info("Source snapshot created for VD %s", device.id)
        return snapshot

    async def _async_sync_entity(
        self, entity: VirtualEntitySourceSnapshot, now: datetime
    ) -> VirtualEntitySyncResult:
        if not entity.source_entity_ids:
            return VirtualEntitySyncResult(
                entity.virtual_entity_id,
                SyncStatus.SKIPPED,
                reason="No current source entities",
                reason_code="no_current_sources",
            )

        statistic_id = self._resolve_statistic_id(entity.virtual_entity_id)
        if not statistic_id:
            return VirtualEntitySyncResult(
                entity.virtual_entity_id,
                SyncStatus.FAILED,
                reason="Virtual entity is not registered in Home Assistant",
                reason_code="entity_not_registered",
            )

        _LOGGER.info("History sync VE %s started", entity.virtual_entity_id)
        try:
            raw_start = now - timedelta(days=get_instance(self._hass).keep_days)
            raw_points = []
            raw_state = RawTimelineState()
            five_minute = []
            hourly = []

            for start, end in self._chunks(raw_start, now, CHUNK_SIZE):
                raw_events = await self._provider.async_read_raw(
                    entity.source_entity_ids, start, end
                )
                points, raw_state = self._aggregator.aggregate_raw(
                    raw_events,
                    entity.device_class,
                    entity.aggregation,
                    raw_state,
                )
                raw_points.extend(points)
                source_slots = await self._provider.async_read_statistics(
                    HistoryResolution.FIVE_MINUTE,
                    entity.source_entity_ids,
                    start,
                    end,
                )
                five_minute.extend(
                    self._aggregator.aggregate_statistics(
                        source_slots,
                        statistic_id,
                        entity.device_class,
                        entity.aggregation,
                        self._completed_five_minute(now),
                    )
                )

            for start, end in self._chunks(self._hourly_history_start, now, CHUNK_SIZE):
                source_slots = await self._provider.async_read_statistics(
                    HistoryResolution.HOUR,
                    entity.source_entity_ids,
                    start,
                    end,
                )
                hourly.extend(
                    self._aggregator.aggregate_statistics(
                        source_slots,
                        statistic_id,
                        entity.device_class,
                        entity.aggregation,
                        now.replace(minute=0, second=0, microsecond=0),
                    )
                )

            if not raw_points and not five_minute and not hourly:
                return VirtualEntitySyncResult(
                    entity.virtual_entity_id,
                    SyncStatus.SKIPPED,
                    reason="No usable historical data",
                    reason_code="no_historical_data",
                )

            # Persistence is deliberately last: failures while reading or calculating
            # cannot alter existing Home Assistant statistics.
            upserted = self._persistence.async_upsert_hourly(
                statistic_id, entity.device_class, hourly
            )
            starts = [point.timestamp for point in raw_points]
            starts.extend(slot.start for slot in five_minute)
            starts.extend(slot.start for slot in hourly)
            resolutions = tuple(
                resolution
                for resolution, values in (
                    (HistoryResolution.RAW, raw_points),
                    (HistoryResolution.FIVE_MINUTE, five_minute),
                    (HistoryResolution.HOUR, hourly),
                )
                if values
            )
            return VirtualEntitySyncResult(
                entity.virtual_entity_id,
                SyncStatus.SUCCESS,
                range_start=min(starts),
                range_end=max(starts),
                resolutions=resolutions,
                hourly_slots_upserted=upserted,
            )
        except Exception as err:  # Per-VE error isolation is intentional.
            _LOGGER.exception("History sync VE %s failed", entity.virtual_entity_id)
            return VirtualEntitySyncResult(
                entity.virtual_entity_id,
                SyncStatus.FAILED,
                reason=str(err),
                reason_code="unexpected_error",
            )

    @staticmethod
    def _chunks(start: datetime, end: datetime, size: timedelta):
        while start < end:
            chunk_end = min(start + size, end)
            yield start, chunk_end
            start = chunk_end

    @staticmethod
    def _completed_five_minute(now: datetime) -> datetime:
        return now.replace(minute=now.minute - now.minute % 5, second=0, microsecond=0)

    @staticmethod
    def _overall_status(results: list[VirtualEntitySyncResult]) -> SyncStatus:
        statuses = {result.status for result in results}
        if not results or statuses == {SyncStatus.SKIPPED}:
            return SyncStatus.SKIPPED
        if statuses <= {SyncStatus.SUCCESS, SyncStatus.SKIPPED}:
            return SyncStatus.SUCCESS
        if SyncStatus.SUCCESS in statuses:
            return SyncStatus.PARTIAL_SUCCESS
        return SyncStatus.FAILED
