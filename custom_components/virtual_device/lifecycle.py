"""Home Assistant registry lifecycle for virtual devices."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers import device_registry, entity_registry, label_registry

from .const import DOMAIN
from .models import VirtualDevice

if TYPE_CHECKING:
    from .sensor import VirtualSensorManager


def virtual_device_identifiers(device_id: str) -> set[tuple[str, str]]:
    """Return the stable Home Assistant identifiers for a virtual device."""
    return {(DOMAIN, device_id)}


def virtual_entity_unique_id(entity_id: str) -> str:
    """Return the stable Home Assistant unique ID for a virtual entity."""
    return f"virtual_device_{entity_id}"


class VirtualDeviceLifecycleManager:
    """Keep VDM runtime objects and Home Assistant registries in sync."""

    def __init__(
        self,
        hass,
        config_entry_id: str,
        sensor_manager: VirtualSensorManager,
    ) -> None:
        """Initialize the lifecycle manager."""
        self._hass = hass
        self._config_entry_id = config_entry_id
        self._sensor_manager = sensor_manager

    def async_ensure_device(
        self,
        device: VirtualDevice,
        name: str | None = None,
    ) -> None:
        """Create or update the Home Assistant device for a VDM device."""
        registry = device_registry.async_get(self._hass)

        entry = registry.async_get_or_create(
            config_entry_id=self._config_entry_id,
            identifiers=virtual_device_identifiers(device.id),
            name=name,
        )

        if name is not None and entry.name != name:
            registry.async_update_device(
                entry.id,
                name=name,
            )

    def _label_name(self, label_ref: str) -> str | None:
        """Return the current display name of a Home Assistant label."""
        entry = label_registry.async_get(self._hass).async_get_label(label_ref)
        return entry.name if entry is not None else None

    def _async_reconcile_device_name(self, device: VirtualDevice) -> None:
        """Set an initial HA device name without replacing an existing one."""
        registry = device_registry.async_get(self._hass)
        entry = registry.async_get_device_by_identifier(
            (DOMAIN, device.id),
            self._config_entry_id,
        )
        label_name = self._label_name(device.label_ref)

        if entry is None:
            self.async_ensure_device(device, name=label_name)
            return

        if entry.name is None and label_name is not None:
            registry.async_update_device(entry.id, name=label_name)

    def get_device_name(
        self,
        device_id: str,
        label_ref: str | None = None,
    ) -> str | None:
        """Return the Home Assistant device name for a VDM device."""
        registry = device_registry.async_get(self._hass)

        entry = registry.async_get_device_by_identifier(
            (DOMAIN, device_id),
            self._config_entry_id,
        )

        if entry is None:
            return self._label_name(label_ref) if label_ref else None

        return (
            entry.name_by_user
            or entry.name
            or (self._label_name(label_ref) if label_ref else None)
        )

    def get_device_registry_id(self, device_id: str) -> str | None:
        """Return the HA registry ID for an existing VDM device."""
        registry = device_registry.async_get(self._hass)
        entry = registry.async_get_device_by_identifier(
            (DOMAIN, device_id),
            self._config_entry_id,
        )
        return entry.id if entry is not None else None

    def get_entity_name(self, entity_id: str) -> str | None:
        """Return the Home Assistant entity name for a VDM entity."""
        registry = entity_registry.async_get(self._hass)

        ha_entity_id = registry.async_get_entity_id(
            "sensor",
            DOMAIN,
            virtual_entity_unique_id(entity_id),
        )

        if ha_entity_id is None:
            return None

        entry = registry.async_get(ha_entity_id)

        if entry is None:
            return None

        return entry.name

    def async_update_entity_name(
        self,
        entity_id: str,
        name: str | None,
    ) -> None:
        """Create or update the Home Assistant entity name."""
        registry = entity_registry.async_get(self._hass)

        ha_entity_id = registry.async_get_entity_id(
            "sensor",
            DOMAIN,
            virtual_entity_unique_id(entity_id),
        )

        if ha_entity_id is None:
            return

        registry.async_update_entity(
            ha_entity_id,
            name=name,
        )

    async def async_remove_entity(self, entity_id: str) -> None:
        """Remove a virtual entity from runtime and the entity registry."""
        await self._sensor_manager.async_remove_entity(entity_id)

        registry = entity_registry.async_get(self._hass)
        ha_entity_id = registry.async_get_entity_id(
            "sensor",
            DOMAIN,
            virtual_entity_unique_id(entity_id),
        )

        if ha_entity_id is not None:
            registry.async_remove(ha_entity_id)

    async def async_remove_device(self, device: VirtualDevice) -> None:
        """Remove all entities and the Home Assistant device for a VDM device."""
        await self.async_remove_device_entities(device)
        self.async_remove_device_registry_entry(device.id)

    async def async_remove_device_entities(self, device: VirtualDevice) -> None:
        """Remove all runtime and registry entities belonging to a device."""
        for entity in device.entities:
            await self.async_remove_entity(entity.id)

        await self._sensor_manager.async_remove_entities_for_device(device.id)
        self._async_remove_orphaned_device_entities(device.id)

    def async_remove_device_registry_entry(self, device_id: str) -> None:
        """Remove the VDM-owned Home Assistant device registry entry."""
        registry = device_registry.async_get(self._hass)
        entry = registry.async_get_device_by_identifier(
            (DOMAIN, device_id),
            self._config_entry_id,
        )

        if entry is not None and entry.config_entries == {self._config_entry_id}:
            registry.async_remove_device(entry.id)

    def _async_remove_orphaned_device_entities(self, device_id: str) -> None:
        """Remove registry entities owned by this device but absent from storage."""
        unique_id_prefix = virtual_entity_unique_id(f"{device_id}_")
        registry = entity_registry.async_get(self._hass)

        for entry in list(registry.entities.values()):
            if not self._is_own_entity(entry):
                continue

            if entry.unique_id.startswith(unique_id_prefix):
                registry.async_remove(entry.entity_id)

    async def async_reconcile(self, devices: list[VirtualDevice]) -> None:
        """Synchronize VDM-owned registry entries with persisted configuration."""
        expected_device_ids = {device.id for device in devices}
        expected_entity_unique_ids = {
            virtual_entity_unique_id(entity.id)
            for device in devices
            for entity in device.entities
        }

        for device in devices:
            self._async_reconcile_device_name(device)
            self.async_reconcile_device_entities(device)

        entity_reg = entity_registry.async_get(self._hass)
        for entry in list(entity_reg.entities.values()):
            if (
                self._is_own_entity(entry)
                and entry.unique_id not in expected_entity_unique_ids
            ):
                await self._sensor_manager.async_remove_entity_by_unique_id(
                    entry.unique_id
                )
                entity_reg.async_remove(entry.entity_id)

        device_reg = device_registry.async_get(self._hass)
        for entry in list(device_reg.devices.values()):
            device_id = self._own_device_id(entry)
            if device_id is None or device_id in expected_device_ids:
                continue

            if entry.config_entries == {self._config_entry_id}:
                device_reg.async_remove_device(entry.id)

    def async_reconcile_device_entities(
        self,
        device: VirtualDevice,
    ) -> None:
        """Ensure VDM entities are assigned to their virtual device."""
        device_reg = device_registry.async_get(self._hass)
        entity_reg = entity_registry.async_get(self._hass)

        device_entry = device_reg.async_get_device_by_identifier(
            (DOMAIN, device.id),
            self._config_entry_id,
        )

        if device_entry is None:
            return

        for virtual_entity in device.entities:
            ha_entity_id = entity_reg.async_get_entity_id(
                "sensor",
                DOMAIN,
                virtual_entity_unique_id(virtual_entity.id),
            )

            if ha_entity_id is None:
                continue

            entity_entry = entity_reg.async_get(ha_entity_id)

            if entity_entry is None:
                continue

            if not self._is_own_entity(entity_entry):
                continue

            if entity_entry.device_id != device_entry.id:
                entity_reg.async_update_entity(
                    ha_entity_id,
                    device_id=device_entry.id,
                )

    def _is_own_entity(self, entry) -> bool:
        """Return whether an entity registry entry is unambiguously VDM-owned."""
        return (
            entry.config_entry_id == self._config_entry_id
            and entry.platform == DOMAIN
            and entry.unique_id.startswith("virtual_device_")
        )

    def _own_device_id(self, entry) -> str | None:
        """Return the VDM device ID when an entry belongs to this integration."""
        if self._config_entry_id not in entry.config_entries:
            return None

        for domain, identifier in entry.identifiers:
            if domain == DOMAIN:
                return identifier

        return None
