"""Base entity for the LazyVolt integration."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DASHBOARD_PATH, DOMAIN
from .coordinator import LazyVoltCoordinator


class LazyVoltEntity(CoordinatorEntity[LazyVoltCoordinator]):
    """An entity on the LazyVolt service device of one config entry."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: LazyVoltCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_translation_key = key
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="LazyVolt",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=f"{entry.data['cloud_url'].rstrip('/')}{DASHBOARD_PATH}",
        )
