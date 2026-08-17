"""Source management for the Virtual Device Manager integration."""

from __future__ import annotations

import asyncio

from homeassistant.core import HomeAssistant

from .aggregator import SourceValue
from .models import VirtualDevice
from .source_finder import get_source_entities, get_source_values

DEFAULT_RECONCILIATION_INTERVAL = 300


class SourceManager:
    """Manage relationships between virtual entities and source entities."""

    def __init__(
        self,
        reconciliation_interval: float = DEFAULT_RECONCILIATION_INTERVAL,
    ) -> None:
        """Initialize the source manager."""
        self._virtual_devices: dict[str, VirtualDevice] = {}
        self._sources_by_virtual_entity: dict[str, set[str]] = {}
        self._virtual_entities_by_source: dict[str, set[str]] = {}

        # Current numeric value of every known source entity.
        #
        # The cache belongs to the physical source entity, not to a
        # virtual entity. A source can therefore be shared by multiple
        # virtual entities without storing its value multiple times.
        self._source_values: dict[str, SourceValue] = {}

        # Interval for the optional periodic reconciliation.
        # 0 disables periodic reconciliation.
        self._reconciliation_interval = reconciliation_interval

        self._reconciliation_task: asyncio.Task[None] | None = None
        self._hass: HomeAssistant | None = None

    @property
    def reconciliation_interval(self) -> float:
        """Return the configured reconciliation interval in seconds."""
        return self._reconciliation_interval

    async def async_start(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Start periodic source reconciliation."""
        if self._reconciliation_task is not None:
            return

        self._hass = hass

        if self._reconciliation_interval <= 0:
            return

        self._reconciliation_task = asyncio.create_task(
            self._async_reconciliation_loop()
        )


    async def async_stop(self) -> None:
        """Stop periodic source reconciliation."""
        task = self._reconciliation_task

        self._reconciliation_task = None
        self._hass = None

        if task is None:
            return

        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass


    async def _async_reconciliation_loop(self) -> None:
        """Run periodic source reconciliation."""
        try:
            while True:
                await asyncio.sleep(
                    self._reconciliation_interval
                )

                if self._hass is not None:
                    await self.async_reconcile(
                        self._hass
                    )

        except asyncio.CancelledError:
            raise

    def add_source(
        self,
        virtual_entity_id: str,
        source_entity_id: str,
    ) -> None:
        """Add a source relationship."""
        self._sources_by_virtual_entity.setdefault(
            virtual_entity_id,
            set(),
        ).add(source_entity_id)

        self._virtual_entities_by_source.setdefault(
            source_entity_id,
            set(),
        ).add(virtual_entity_id)

    def remove_source(
        self,
        virtual_entity_id: str,
        source_entity_id: str,
    ) -> None:
        """Remove a source relationship."""
        sources = self._sources_by_virtual_entity.get(
            virtual_entity_id
        )

        if sources is not None:
            sources.discard(source_entity_id)

            if not sources:
                self._sources_by_virtual_entity.pop(
                    virtual_entity_id,
                    None,
                )

        virtual_entities = self._virtual_entities_by_source.get(
            source_entity_id
        )

        if virtual_entities is not None:
            virtual_entities.discard(virtual_entity_id)

            if not virtual_entities:
                self._virtual_entities_by_source.pop(
                    source_entity_id,
                    None,
                )

                # The source is no longer used by any virtual entity.
                self._source_values.pop(
                    source_entity_id,
                    None,
                )

    def get_sources(self, virtual_entity_id: str) -> list[str]:
        """Return source entities for a virtual entity."""
        return sorted(
            self._sources_by_virtual_entity.get(
                virtual_entity_id,
                set(),
            )
        )

    def get_virtual_entities(
        self,
        source_entity_id: str,
    ) -> list[str]:
        """Return virtual entities using a source entity."""
        return sorted(
            self._virtual_entities_by_source.get(
                source_entity_id,
                set(),
            )
        )

    def get_source_value(
        self,
        source_entity_id: str,
    ) -> SourceValue | None:
        """Return the cached value of a source entity."""
        return self._source_values.get(source_entity_id)

    def get_source_values(
        self,
        virtual_entity_id: str,
    ) -> list[SourceValue]:
        """Return all cached source values for a virtual entity."""
        return [
            self._source_values[source_entity_id]
            for source_entity_id in self.get_sources(
                virtual_entity_id
            )
            if source_entity_id in self._source_values
        ]

    def update_source_value(
        self,
        source_value: SourceValue,
    ) -> list[str]:
        """Update a cached source value and return affected virtual entities."""
        self._source_values[source_value.entity_id] = source_value

        return self.get_affected_virtual_entities(
            source_value.entity_id
        )

    def remove_source_value(
        self,
        source_entity_id: str,
    ) -> list[str]:
        """Remove a source value from the cache."""
        self._source_values.pop(
            source_entity_id,
            None,
        )

        return self.get_affected_virtual_entities(
            source_entity_id
        )

    def clear(self) -> None:
        """Clear all source relationships and cached values."""
        self._sources_by_virtual_entity.clear()
        self._virtual_entities_by_source.clear()
        self._source_values.clear()
        self._virtual_devices.clear()

    def rebuild_virtual_device(
        self,
        hass: HomeAssistant,
        device: VirtualDevice,
    ) -> None:
        """Rebuild source relationships for a virtual device."""

        self._virtual_devices[device.id] = device

        for virtual_entity in device.entities:
            virtual_entity_id = virtual_entity.id

            # Remove existing relationships first.
            for source_entity_id in self.get_sources(
                virtual_entity_id
            ):
                self.remove_source(
                    virtual_entity_id,
                    source_entity_id,
                )

            source_entities = get_source_entities(
                hass,
                device.label_ref,
                virtual_entity.device_class,
            )

            for source_entity_id in source_entities:
                self.add_source(
                    virtual_entity_id,
                    source_entity_id,
                )

        # Rebuild cached values for the sources currently used by
        # this virtual device.
        for virtual_entity in device.entities:
            source_values = get_source_values(
                hass,
                device.label_ref,
                virtual_entity.device_class,
            )

            for source_value in source_values:
                self._source_values[
                    source_value.entity_id
                ] = source_value

    async def async_reconcile(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Reconcile source relationships and cached values."""
        for device in self._virtual_devices.values():
            for virtual_entity in device.entities:
                virtual_entity_id = virtual_entity.id

                current_sources = set(
                    self.get_sources(virtual_entity_id)
                )

                discovered_sources = set(
                    get_source_entities(
                        hass,
                        device.label_ref,
                        virtual_entity.device_class,
                    )
                )

                # Remove sources that no longer match.
                for source_entity_id in (
                    current_sources - discovered_sources
                ):
                    self.remove_source(
                        virtual_entity_id,
                        source_entity_id,
                    )

                # Add newly matching sources.
                for source_entity_id in (
                    discovered_sources - current_sources
                ):
                    self.add_source(
                        virtual_entity_id,
                        source_entity_id,
                    )

        # Rebuild the value cache from the now-current relationships.
        reconciled_values: dict[str, SourceValue] = {}

        source_entity_ids = set(
            self._virtual_entities_by_source
        )

        for source_entity_id in source_entity_ids:
            state = hass.states.get(source_entity_id)

            if state is None:
                continue

            if state.state in ("unknown", "unavailable"):
                continue

            try:
                value = float(state.state)
            except (TypeError, ValueError):
                continue

            unit = state.attributes.get(
                "unit_of_measurement"
            )

            if not unit:
                continue

            reconciled_values[source_entity_id] = SourceValue(
                entity_id=source_entity_id,
                value=value,
                unit=unit,
            )

        self._source_values = reconciled_values

    def get_affected_virtual_entities(
        self,
        source_entity_id: str,
    ) -> list[str]:
        """Return virtual entities affected by a source change."""
        return self.get_virtual_entities(source_entity_id)

    def handle_source_change(
        self,
        source_entity_id: str,
    ) -> list[str]:
        """Return virtual entities affected by a source change."""
        return self.get_affected_virtual_entities(
            source_entity_id
        )
    