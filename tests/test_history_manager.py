"""Tests for explicit history synchronization orchestration."""

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.virtual_device.history.manager import (
    HistorySyncBusyError,
    HistorySyncManager,
)
from custom_components.virtual_device.history.models import (
    HistoryResolution,
    StatisticsSlot,
    SyncStatus,
)
from custom_components.virtual_device.models import VirtualDevice, VirtualEntity


def device() -> VirtualDevice:
    return VirtualDevice(
        "lighting",
        "lighting",
        [VirtualEntity("energy", "energy", "sum")],
    )


def source_manager(sources=("sensor.a",)):
    manager = MagicMock()
    manager.async_reconcile = AsyncMock()
    manager.get_sources.return_value = list(sources)
    return manager


@pytest.mark.asyncio
async def test_sync_reconciles_freezes_sources_and_persists_hourly_only() -> None:
    now = datetime.now(UTC)
    provider = MagicMock()
    provider.async_read_raw = AsyncMock(return_value=())

    async def read_statistics(resolution, entity_ids, start, end):
        assert entity_ids == ("sensor.a",)
        if resolution is HistoryResolution.HOUR:
            return (StatisticsSlot("sensor.a", now - timedelta(hours=2), "Wh", sum=10),)
        return ()

    provider.async_read_statistics = AsyncMock(side_effect=read_statistics)
    persistence = MagicMock()
    persistence.async_upsert_hourly.return_value = 1
    sources = source_manager()
    manager = HistorySyncManager(
        MagicMock(),
        sources,
        lambda _: "sensor.virtual_energy",
        provider=provider,
        persistence=persistence,
        hourly_history_start=now - timedelta(days=1),
    )

    with patch(
        "custom_components.virtual_device.history.manager.get_instance",
        return_value=SimpleNamespace(keep_days=1),
    ):
        result = await manager.async_sync(device())

    sources.async_reconcile.assert_awaited_once()
    assert result.status is SyncStatus.SUCCESS
    assert result.entities[0].hourly_slots_upserted == 1
    persistence.async_upsert_hourly.assert_called_once()


@pytest.mark.asyncio
async def test_no_sources_is_skipped_without_reads_or_persistence() -> None:
    provider = MagicMock()
    persistence = MagicMock()
    manager = HistorySyncManager(
        MagicMock(),
        source_manager(()),
        lambda _: "sensor.virtual_energy",
        provider=provider,
        persistence=persistence,
    )

    result = await manager.async_sync(device())

    assert result.entities[0].status is SyncStatus.SKIPPED
    assert result.entities[0].reason == "No current source entities"
    provider.async_read_raw.assert_not_called()
    persistence.async_upsert_hourly.assert_not_called()


@pytest.mark.asyncio
async def test_read_failure_does_not_persist_and_releases_lock() -> None:
    provider = MagicMock()
    provider.async_read_raw = AsyncMock(side_effect=RuntimeError("read failed"))
    persistence = MagicMock()
    manager = HistorySyncManager(
        MagicMock(),
        source_manager(),
        lambda _: "sensor.virtual_energy",
        provider=provider,
        persistence=persistence,
    )

    with patch(
        "custom_components.virtual_device.history.manager.get_instance",
        return_value=SimpleNamespace(keep_days=1),
    ):
        first = await manager.async_sync(device())
        second = await manager.async_sync(device())

    assert first.status is SyncStatus.FAILED
    assert second.status is SyncStatus.FAILED
    persistence.async_upsert_hourly.assert_not_called()


@pytest.mark.asyncio
async def test_global_concurrency_rejects_second_request() -> None:
    entered = asyncio.Event()
    release = asyncio.Event()
    provider = MagicMock()

    async def blocking_read(*args):
        entered.set()
        await release.wait()
        return ()

    provider.async_read_raw = AsyncMock(side_effect=blocking_read)
    provider.async_read_statistics = AsyncMock(return_value=())
    manager = HistorySyncManager(
        MagicMock(),
        source_manager(),
        lambda _: "sensor.virtual_energy",
        provider=provider,
        persistence=MagicMock(),
        hourly_history_start=datetime.now(UTC),
    )

    with patch(
        "custom_components.virtual_device.history.manager.get_instance",
        return_value=SimpleNamespace(keep_days=1),
    ):
        task = asyncio.create_task(manager.async_sync(device()))
        await entered.wait()
        with pytest.raises(HistorySyncBusyError):
            await manager.async_sync(device())
        release.set()
        await task
