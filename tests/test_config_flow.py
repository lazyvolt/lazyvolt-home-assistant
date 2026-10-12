"""Tests for the LazyVolt config flow."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.lazyvolt.api import LazyVoltApiError, LazyVoltAuthError
from custom_components.lazyvolt.const import (
    CONF_CLOUD_TOKEN,
    CONF_PEBLAR_ENTRY_ID,
    DOMAIN,
    PEBLAR_DOMAIN,
    PRODUCTION_CLOUD_URL,
)
from tests.conftest import MOCK_CLOUD_URL, MOCK_PEBLAR_ENTRY_ID, MOCK_TOKEN


async def test_user_step_success_single_peblar_dev_mode(hass, mock_peblar_entry):
    """Dev mode: URL field shown; auth succeeds, single Peblar → entry created."""
    mock_peblar_entry.add_to_hass(hass)

    with patch("custom_components.lazyvolt.config_flow._DEV_MODE", True), patch(
        "custom_components.lazyvolt.config_flow.LazyVoltApiClient.authenticate",
        new_callable=AsyncMock,
        return_value=MOCK_TOKEN,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] == "form"
        assert result["step_id"] == "user"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "cloud_url": MOCK_CLOUD_URL,
                "edge_name": "Home Assistant",
                "email": "user@example.com",
                "password": "secret",
            },
        )

    assert result["type"] == "create_entry"
    assert result["data"]["cloud_url"] == MOCK_CLOUD_URL
    assert result["data"][CONF_CLOUD_TOKEN] == MOCK_TOKEN
    assert result["data"][CONF_PEBLAR_ENTRY_ID] == MOCK_PEBLAR_ENTRY_ID


async def test_user_step_success_single_peblar_production(hass, mock_peblar_entry):
    """Production mode: no URL field; cloud URL hardcoded to production URL."""
    mock_peblar_entry.add_to_hass(hass)

    with patch("custom_components.lazyvolt.config_flow._DEV_MODE", False), patch(
        "custom_components.lazyvolt.config_flow.LazyVoltApiClient.authenticate",
        new_callable=AsyncMock,
        return_value=MOCK_TOKEN,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] == "form"
        assert result["step_id"] == "user"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"edge_name": "Home Assistant", "email": "user@example.com", "password": "secret"},
        )

    assert result["type"] == "create_entry"
    assert result["data"]["cloud_url"] == PRODUCTION_CLOUD_URL
    assert result["data"][CONF_CLOUD_TOKEN] == MOCK_TOKEN


async def test_user_step_multiple_peblar_shows_selection(hass):
    """Multiple Peblar entries → peblar selection step is shown."""
    entry_a = MockConfigEntry(domain=PEBLAR_DOMAIN, title="Charger A", entry_id="entry_a")
    entry_b = MockConfigEntry(domain=PEBLAR_DOMAIN, title="Charger B", entry_id="entry_b")
    entry_a.add_to_hass(hass)
    entry_b.add_to_hass(hass)

    with patch("custom_components.lazyvolt.config_flow._DEV_MODE", False), patch(
        "custom_components.lazyvolt.config_flow.LazyVoltApiClient.authenticate",
        new_callable=AsyncMock,
        return_value=MOCK_TOKEN,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"edge_name": "HA", "email": "u@e.com", "password": "p"},
        )

    assert result["type"] == "form"
    assert result["step_id"] == "peblar"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PEBLAR_ENTRY_ID: "entry_b"}
    )
    assert result["type"] == "create_entry"
    assert result["data"][CONF_PEBLAR_ENTRY_ID] == "entry_b"


async def test_user_step_invalid_auth_shows_error(hass, mock_peblar_entry):
    """Wrong credentials show an error, form is re-displayed."""
    mock_peblar_entry.add_to_hass(hass)

    with patch("custom_components.lazyvolt.config_flow._DEV_MODE", False), patch(
        "custom_components.lazyvolt.config_flow.LazyVoltApiClient.authenticate",
        new_callable=AsyncMock,
        side_effect=LazyVoltAuthError("Invalid credentials"),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"edge_name": "HA", "email": "bad@e.com", "password": "wrong"},
        )

    assert result["type"] == "form"
    assert result["errors"]["base"] == "invalid_auth"


async def test_user_step_cannot_connect_shows_error(hass, mock_peblar_entry):
    """Connection failure shows an error."""
    mock_peblar_entry.add_to_hass(hass)

    with patch("custom_components.lazyvolt.config_flow._DEV_MODE", False), patch(
        "custom_components.lazyvolt.config_flow.LazyVoltApiClient.authenticate",
        new_callable=AsyncMock,
        side_effect=LazyVoltApiError("Cannot connect"),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"edge_name": "HA", "email": "u@e.com", "password": "p"},
        )

    assert result["type"] == "form"
    assert result["errors"]["base"] == "cannot_connect"


async def test_no_peblar_aborts_flow(hass):
    """No Peblar integration installed → flow aborts before asking for credentials."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == "abort"
    assert result["reason"] == "no_peblar"


async def test_same_charger_cannot_be_added_twice(hass, mock_config_entry, mock_peblar_entry):
    """Charger already controlled → abort before logging in, so Cloud keeps the existing token."""
    mock_peblar_entry.add_to_hass(hass)
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.lazyvolt.config_flow.LazyVoltApiClient.authenticate",
        new_callable=AsyncMock,
    ) as authenticate:
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

    assert result["type"] == "abort"
    assert result["reason"] == "already_configured"
    authenticate.assert_not_called()


async def test_second_charger_with_same_edge_name_shows_error(hass, mock_config_entry, mock_peblar_entry):
    """Reusing an edge name would revoke the first charger's token in Cloud → rejected in the form."""
    mock_peblar_entry.add_to_hass(hass)
    MockConfigEntry(domain=PEBLAR_DOMAIN, title="Garage", entry_id="entry_garage").add_to_hass(hass)
    mock_config_entry.add_to_hass(hass)

    with patch("custom_components.lazyvolt.config_flow._DEV_MODE", False), patch(
        "custom_components.lazyvolt.config_flow.LazyVoltApiClient.authenticate",
        new_callable=AsyncMock,
    ) as authenticate:
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"edge_name": "Home Assistant", "email": "u@e.com", "password": "p"},
        )

    assert result["errors"]["edge_name"] == "edge_name_in_use"
    authenticate.assert_not_called()


async def test_second_charger_is_auto_selected(hass, mock_config_entry, mock_peblar_entry):
    """First charger already controlled → the remaining one is picked without asking."""
    mock_peblar_entry.add_to_hass(hass)
    MockConfigEntry(domain=PEBLAR_DOMAIN, title="Garage", entry_id="entry_garage").add_to_hass(hass)
    mock_config_entry.add_to_hass(hass)

    with patch("custom_components.lazyvolt.config_flow._DEV_MODE", False), patch(
        "custom_components.lazyvolt.config_flow.LazyVoltApiClient.authenticate",
        new_callable=AsyncMock,
        return_value=MOCK_TOKEN,
    ), patch("custom_components.lazyvolt.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"edge_name": "Garage", "email": "u@e.com", "password": "p"},
        )

    assert result["type"] == "create_entry"
    assert result["data"][CONF_PEBLAR_ENTRY_ID] == "entry_garage"
    assert result["result"].unique_id == "entry_garage"


async def test_reauth_stores_new_token(hass, mock_config_entry):
    """Token revoked in Cloud → user logs in again → entry gets the fresh token."""
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.lazyvolt.config_flow.LazyVoltApiClient.authenticate",
        new_callable=AsyncMock,
        return_value="2|fresh_token",
    ) as authenticate, patch("custom_components.lazyvolt.async_setup_entry", return_value=True):
        result = await mock_config_entry.start_reauth_flow(hass)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"email": "u@e.com", "password": "p"}
        )
        await hass.async_block_till_done()

    assert result["reason"] == "reauth_successful"
    assert mock_config_entry.data[CONF_CLOUD_TOKEN] == "2|fresh_token"
    assert authenticate.call_args[0][2] == "Home Assistant"


async def test_reauth_with_wrong_password_shows_error(hass, mock_config_entry):
    """Wrong password during reauth keeps the form open and the old token in place."""
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.lazyvolt.config_flow.LazyVoltApiClient.authenticate",
        new_callable=AsyncMock,
        side_effect=LazyVoltAuthError("Invalid credentials"),
    ):
        result = await mock_config_entry.start_reauth_flow(hass)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"email": "u@e.com", "password": "wrong"}
        )

    assert result["errors"]["base"] == "invalid_auth"
    assert mock_config_entry.data[CONF_CLOUD_TOKEN] == MOCK_TOKEN
