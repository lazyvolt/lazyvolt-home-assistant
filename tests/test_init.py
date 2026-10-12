"""Tests for LazyVolt setup and unload."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntryState

from custom_components.lazyvolt.api import LazyVoltAuthError
from custom_components.lazyvolt.const import DOMAIN
from tests.conftest import MOCK_PEBLAR_ENTRY_ID


async def test_setup_creates_service_device_with_entities(hass, setup_integration):
    """After setup the user can see mode and Cloud connection in HA."""
    assert setup_integration.state is ConfigEntryState.LOADED
    assert hass.states.get("sensor.lazyvolt_home_assistant_charge_mode") is not None
    assert hass.states.get("binary_sensor.lazyvolt_home_assistant_cloud_connection") is not None


async def test_entry_from_v0_1_gets_peblar_unique_id(hass, setup_integration):
    """Entries created before unique ids existed are backfilled so duplicates can be detected."""
    assert setup_integration.unique_id == MOCK_PEBLAR_ENTRY_ID


async def test_unload_removes_entities(hass, setup_integration):
    """Removing the integration unloads its platforms cleanly."""
    assert await hass.config_entries.async_unload(setup_integration.entry_id)

    assert setup_integration.state is ConfigEntryState.NOT_LOADED


async def test_token_revoked_before_startup_prompts_reauth(hass, mock_config_entry, mock_api):
    """Token revoked while HA was off → setup fails and the user is asked to log in again."""
    mock_api.get_decision = AsyncMock(side_effect=LazyVoltAuthError("Cloud token rejected"))
    mock_config_entry.add_to_hass(hass)

    with patch("custom_components.lazyvolt.LazyVoltApiClient", return_value=mock_api):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR
    assert flows[0]["context"]["source"] == SOURCE_REAUTH
