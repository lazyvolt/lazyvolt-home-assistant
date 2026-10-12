"""LazyVolt Cloud → Peblar charge controller integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client

from .api import LazyVoltApiClient
from .const import CONF_CLOUD_TOKEN, CONF_PEBLAR_ENTRY_ID, DOMAIN, PLATFORMS
from .coordinator import LazyVoltCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up LazyVolt from a config entry."""
    _ensure_unique_id(hass, entry)
    session = aiohttp_client.async_get_clientsession(hass)
    api = LazyVoltApiClient(
        entry.data["cloud_url"],
        session,
        entry.data[CONF_CLOUD_TOKEN],
    )
    coordinator = LazyVoltCoordinator(hass, entry, api)
    coordinator.setup_entity_ids()
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


def _ensure_unique_id(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Backfill the Peblar-based unique id on entries created before v1.0.0."""
    if entry.unique_id is not None:
        return
    peblar_entry_id = entry.data[CONF_PEBLAR_ENTRY_ID]
    taken = {e.unique_id for e in hass.config_entries.async_entries(DOMAIN)}
    if peblar_entry_id not in taken:
        hass.config_entries.async_update_entry(entry, unique_id=peblar_entry_id)
