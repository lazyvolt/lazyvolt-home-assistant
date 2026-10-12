"""Config flow for the LazyVolt integration."""
from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import LazyVoltApiClient, LazyVoltApiError, LazyVoltAuthError
from .const import (
    CONF_CLOUD_TOKEN,
    CONF_PEBLAR_ENTRY_ID,
    DEFAULT_CLOUD_URL,
    DEFAULT_EDGE_NAME,
    DOMAIN,
    PEBLAR_DOMAIN,
    PRODUCTION_CLOUD_URL,
)

_DEV_MODE = bool(os.environ.get("LAZYVOLT_DEV"))

_CREDENTIAL_FIELDS: dict = {
    vol.Required("email"): TextSelector(TextSelectorConfig(type=TextSelectorType.EMAIL)),
    vol.Required("password"): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD)),
}


class LazyVoltConfigFlow(ConfigFlow, domain=DOMAIN):
    """Two-step config flow: Cloud auth → Peblar device selection."""

    VERSION = 1

    def __init__(self) -> None:
        self._cloud_url: str = DEFAULT_CLOUD_URL
        self._edge_name: str = DEFAULT_EDGE_NAME
        self._token: str = ""

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        # Abort before authenticating: Cloud revokes the existing token of an edge
        # that logs in again, which would break an already configured entry.
        if not self._peblar_entries():
            return self.async_abort(reason="no_peblar")
        if not self._unconfigured_peblar_entries():
            return self.async_abort(reason="already_configured")

        errors: dict[str, str] = {}

        if user_input is not None:
            cloud_url = user_input.get("cloud_url", PRODUCTION_CLOUD_URL)
            edge_name = user_input["edge_name"]
            if edge_name in self._configured_edge_names():
                errors["edge_name"] = "edge_name_in_use"
            else:
                token, error = await self._authenticate(cloud_url, user_input, edge_name)
                if token:
                    self._cloud_url = cloud_url
                    self._edge_name = edge_name
                    self._token = token
                    return await self.async_step_peblar()
                errors["base"] = error

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(self._user_fields()),
            description_placeholders={"lazyvolt_url": "lazyvolt.com"},
            errors=errors,
        )

    async def async_step_peblar(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return await self._create_entry(user_input[CONF_PEBLAR_ENTRY_ID])

        peblar_entries = self._unconfigured_peblar_entries()

        # Auto-advance if exactly one Peblar device is available
        if len(peblar_entries) == 1:
            return await self._create_entry(peblar_entries[0].entry_id)

        options = [
            SelectOptionDict(value=e.entry_id, label=e.title) for e in peblar_entries
        ]

        return self.async_show_form(
            step_id="peblar",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PEBLAR_ENTRY_ID): SelectSelector(
                        SelectSelectorConfig(options=options)
                    ),
                }
            ),
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Cloud rejected the stored token — ask for credentials again."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            token, error = await self._authenticate(
                entry.data["cloud_url"], user_input, entry.data["edge_name"]
            )
            if token:
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_CLOUD_TOKEN: token}
                )
            errors["base"] = error

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(_CREDENTIAL_FIELDS),
            description_placeholders={"edge_name": entry.data["edge_name"]},
            errors=errors,
        )

    async def _authenticate(
        self, cloud_url: str, credentials: dict, edge_name: str
    ) -> tuple[str | None, str]:
        """Exchange credentials for an edge token; returns (token, error key)."""
        session = aiohttp_client.async_get_clientsession(self.hass)
        api = LazyVoltApiClient(cloud_url, session)
        try:
            token = await api.authenticate(
                credentials["email"], credentials["password"], edge_name
            )
        except LazyVoltAuthError:
            return None, "invalid_auth"
        except LazyVoltApiError:
            return None, "cannot_connect"
        return token, ""

    async def _create_entry(self, peblar_entry_id: str) -> ConfigFlowResult:
        await self.async_set_unique_id(peblar_entry_id)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=f"LazyVolt ({self._edge_name})",
            data={
                "cloud_url": self._cloud_url,
                "edge_name": self._edge_name,
                CONF_CLOUD_TOKEN: self._token,
                CONF_PEBLAR_ENTRY_ID: peblar_entry_id,
            },
        )

    def _user_fields(self) -> dict:
        fields: dict = {
            vol.Required("edge_name", default=DEFAULT_EDGE_NAME): str,
            **_CREDENTIAL_FIELDS,
        }
        if not _DEV_MODE:
            return fields
        return {
            vol.Required("cloud_url", default=DEFAULT_CLOUD_URL): TextSelector(
                TextSelectorConfig(type=TextSelectorType.URL)
            ),
            **fields,
        }

    def _peblar_entries(self) -> list[ConfigEntry]:
        return self.hass.config_entries.async_entries(PEBLAR_DOMAIN)

    def _unconfigured_peblar_entries(self) -> list[ConfigEntry]:
        configured = {e.data.get(CONF_PEBLAR_ENTRY_ID) for e in self._async_current_entries()}
        return [e for e in self._peblar_entries() if e.entry_id not in configured]

    def _configured_edge_names(self) -> set[str]:
        return {e.data.get("edge_name") for e in self._async_current_entries()}
