"""Supported Home Assistant persistence for prepared VDM history."""

from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum

from homeassistant.components.recorder.models import (
    StatisticData,
    StatisticMetaData,
)
from homeassistant.components.recorder.statistics import (
    STATISTIC_UNIT_TO_UNIT_CONVERTER,
    async_import_statistics,
)
from homeassistant.components.sensor import SensorStateClass
from homeassistant.core import HomeAssistant

from ..device_class_metadata import get_device_class_metadata
from .models import StatisticsSlot

try:
    from homeassistant.components.recorder.models import StatisticMeanType
except ImportError:  # Compatibility for the older HA test runtime.

    class StatisticMeanType(StrEnum):
        """HA 2026.8 statistic mean types used by VDM metadata."""

        NONE = "none"
        ARITHMETIC = "arithmetic"
        CIRCULAR = "circular"


PERSISTENCE_MODE = "hourly_upsert"


class HistoryPersistenceAdapter:
    """Persist hourly statistics through Home Assistant's public import API.

    Home Assistant 2026.8 has no supported raw-state or five-minute import API,
    nor a transactional range-replacement API. V1 therefore upserts only the
    recalculated hourly slots. Obsolete slots absent from a later calculation
    intentionally remain untouched.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass

    def async_upsert_hourly(
        self,
        statistic_id: str,
        device_class: str,
        slots: Iterable[StatisticsSlot],
    ) -> int:
        """Queue supported hourly internal-statistics upserts."""
        slot_list = list(slots)
        if not slot_list:
            return 0

        metadata = self._metadata(statistic_id, device_class)
        statistics = [self._statistic_data(slot, metadata) for slot in slot_list]
        async_import_statistics(self._hass, metadata, statistics)
        return len(statistics)

    @staticmethod
    def _metadata(statistic_id: str, device_class: str) -> StatisticMetaData:
        device_metadata = get_device_class_metadata(device_class)
        state_class = device_metadata.state_class
        unit = device_metadata.native_unit
        converter = STATISTIC_UNIT_TO_UNIT_CONVERTER.get(unit)
        unit_class = converter.UNIT_CLASS if converter is not None else None
        return {
            "statistic_id": statistic_id,
            "source": "recorder",
            "name": None,
            "unit_of_measurement": unit,
            "unit_class": unit_class,
            "mean_type": (
                StatisticMeanType.ARITHMETIC
                if state_class is SensorStateClass.MEASUREMENT
                else StatisticMeanType.NONE
            ),
            "has_sum": state_class is SensorStateClass.TOTAL_INCREASING,
        }

    @staticmethod
    def _statistic_data(
        slot: StatisticsSlot, metadata: StatisticMetaData
    ) -> StatisticData:
        result: StatisticData = {"start": slot.start}
        if metadata["has_sum"]:
            if slot.state is not None:
                result["state"] = slot.state
            if slot.sum is not None:
                result["sum"] = slot.sum
            if slot.last_reset is not None:
                result["last_reset"] = slot.last_reset
        else:
            if slot.mean is not None:
                result["mean"] = slot.mean
            if slot.minimum is not None:
                result["min"] = slot.minimum
            if slot.maximum is not None:
                result["max"] = slot.maximum
        return result
