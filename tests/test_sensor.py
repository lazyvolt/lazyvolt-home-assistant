"""Tests for LazyVolt sensors."""
from __future__ import annotations

from unittest.mock import AsyncMock

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN

from custom_components.lazyvolt.api import LazyVoltApiError

MODE = "sensor.lazyvolt_home_assistant_charge_mode"
LAST_DECISION = "sensor.lazyvolt_home_assistant_last_decision"


async def _refresh(hass, entry) -> None:
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()


async def test_mode_sensor_shows_cloud_mode(hass, setup_integration, mock_api):
    """Cloud says MAX → the mode sensor reads max."""
    mock_api.get_decision = AsyncMock(return_value={"mode": "MAX"})

    await _refresh(hass, setup_integration)

    assert hass.states.get(MODE).state == "max"


async def test_unrecognised_mode_shows_unknown(hass, setup_integration, mock_api):
    """Cloud sends a mode this version doesn't know → unknown, not a guess."""
    mock_api.get_decision = AsyncMock(return_value={"mode": "TURBO"})

    await _refresh(hass, setup_integration)

    assert hass.states.get(MODE).state == STATE_UNKNOWN


async def test_cloud_outage_keeps_last_decision_time(hass, setup_integration, mock_api):
    """During an outage the mode is unavailable but the last decision time stays visible."""
    last_decision = hass.states.get(LAST_DECISION).state
    mock_api.get_decision = AsyncMock(side_effect=LazyVoltApiError("Cannot connect"))

    await _refresh(hass, setup_integration)

    assert hass.states.get(MODE).state == STATE_UNAVAILABLE
    assert hass.states.get(LAST_DECISION).state == last_decision
