"""Tests for the LazyVolt Cloud connection sensor."""
from __future__ import annotations

from unittest.mock import AsyncMock

from homeassistant.const import STATE_OFF, STATE_ON

from custom_components.lazyvolt.api import LazyVoltApiError

CLOUD_CONNECTION = "binary_sensor.lazyvolt_home_assistant_cloud_connection"


async def test_cloud_connection_on_while_cloud_answers(hass, setup_integration):
    """Successful decision poll → connected."""
    assert hass.states.get(CLOUD_CONNECTION).state == STATE_ON


async def test_cloud_outage_turns_connection_off(hass, setup_integration, mock_api):
    """Cloud unreachable → connection reads off instead of going unavailable."""
    mock_api.get_decision = AsyncMock(side_effect=LazyVoltApiError("Cannot connect"))

    await setup_integration.runtime_data.async_refresh()
    await hass.async_block_till_done()

    assert hass.states.get(CLOUD_CONNECTION).state == STATE_OFF
