"""Sensors exposing the current LazyVolt decision."""
from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CloudMode
from .coordinator import LazyVoltCoordinator
from .entity import LazyVoltEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up LazyVolt sensors."""
    coordinator: LazyVoltCoordinator = entry.runtime_data
    async_add_entities([LazyVoltModeSensor(coordinator), LazyVoltLastDecisionSensor(coordinator)])


class LazyVoltModeSensor(LazyVoltEntity, SensorEntity):
    """The charge mode Cloud dictates right now; unknown when the decision is unrecognised."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = [mode.value.lower() for mode in CloudMode]

    def __init__(self, coordinator: LazyVoltCoordinator) -> None:
        super().__init__(coordinator, "mode")

    @property
    def native_value(self) -> str | None:
        mode: CloudMode | None = self.coordinator.data["mode"]
        return mode.value.lower() if mode else None


class LazyVoltLastDecisionSensor(LazyVoltEntity, SensorEntity):
    """When Cloud last answered; keeps its value through outages so the gap is visible."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: LazyVoltCoordinator) -> None:
        super().__init__(coordinator, "last_decision")

    @property
    def available(self) -> bool:
        return self.coordinator.data is not None

    @property
    def native_value(self) -> datetime | None:
        return self.coordinator.data["decision_at"]
