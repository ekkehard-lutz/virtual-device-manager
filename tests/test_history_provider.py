"""Tests for Recorder history normalization."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import State

from custom_components.virtual_device.history.models import HistoryResolution
from custom_components.virtual_device.history.provider import HistoricalDataProvider

BASE = datetime(2026, 1, 1, tzinfo=UTC)


def test_raw_normalization_preserves_invalidations_units_and_timestamps() -> None:
    result = HistoricalDataProvider._normalize_raw(
        {
            "sensor.a": [
                State("sensor.a", "10", {"unit_of_measurement": "W"}, BASE, BASE),
                State(
                    "sensor.a",
                    "unavailable",
                    {"unit_of_measurement": "kW"},
                    BASE,
                    BASE,
                ),
            ]
        }
    )

    assert result[0].value == 10
    assert result[0].unit == "W"
    assert result[0].timestamp == BASE
    assert result[1].value is None


def test_statistics_normalization_preserves_fields() -> None:
    result = HistoricalDataProvider._normalize_statistics(
        {
            "sensor.a": [
                {
                    "start": BASE.timestamp(),
                    "mean": 10,
                    "min": 5,
                    "max": 15,
                    "state": 20,
                    "sum": 100,
                    "last_reset": BASE.timestamp(),
                }
            ]
        },
        {"sensor.a": (1, {"unit_of_measurement": "W"})},
    )

    slot = result[0]
    assert slot.start == BASE
    assert slot.unit == "W"
    assert (slot.mean, slot.minimum, slot.maximum, slot.state, slot.sum) == (
        10,
        5,
        15,
        20,
        100,
    )
    assert slot.last_reset == BASE


@pytest.mark.asyncio
async def test_raw_read_uses_recorder_executor_and_full_changes() -> None:
    recorder = MagicMock()
    recorder.async_add_executor_job = AsyncMock(return_value={})
    provider = HistoricalDataProvider(MagicMock())

    with patch(
        "custom_components.virtual_device.history.provider.get_instance",
        return_value=recorder,
    ):
        result = await provider.async_read_raw(("sensor.a",), BASE, BASE)

    assert result == ()
    args = recorder.async_add_executor_job.await_args.args
    assert args[4] == ["sensor.a"]
    assert args[6] is True
    assert args[7] is False


@pytest.mark.asyncio
async def test_statistics_read_rejects_raw_resolution() -> None:
    with pytest.raises(ValueError):
        await HistoricalDataProvider(MagicMock()).async_read_statistics(
            HistoryResolution.RAW, ("sensor.a",), BASE, BASE
        )
