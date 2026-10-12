"""Binary sensor reporting LazyVolt Cloud connectivity."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import LazyVoltCoordinator
from .entity import LazyVoltEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the LazyVolt connectivity sensor."""
    coordinator: LazyVoltCoordinator = entry.runtime_data
    async_add_entities([LazyVoltCloudConnectedSensor(coordinator)])


class LazyVoltCloudConnectedSensor(LazyVoltEntity, BinarySensorEntity):
    """On while the last Cloud poll succeeded; stays available so outages read as off."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: LazyVoltCoordinator) -> None:
        super().__init__(coordinator, "cloud_connected")

    @property
    def available(self) -> bool:
        return True

    @property
    def is_on(self) -> bool:
        return self.coordinator.last_update_success
