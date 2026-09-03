"""The PlaiiinLight integration."""
from __future__ import annotations

from typing import Any

from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import LamposClient
from .const import CONF_DEVICE_ID, CONF_NODE, CONF_SHARE_KEY, DEFAULT_PORT
from .coordinator import PlaiiinLightConfigEntry, PlaiiinLightCoordinator

PLATFORMS: list[Platform] = [Platform.LIGHT]


async def async_setup_entry(hass: HomeAssistant, entry: PlaiiinLightConfigEntry) -> bool:
    """Set up a lamp from a config entry."""
    client = LamposClient(
        async_get_clientsession(hass),
        entry.data[CONF_HOST],
        entry.data.get(CONF_PORT, DEFAULT_PORT),
        entry.data.get(CONF_SHARE_KEY),
    )
    coordinator = PlaiiinLightCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    # Existing entries keep their node-name unique_id (no registry
    # migration). But once we've talked to the lamp we can learn its
    # stable device id for future rename-dedupe, and follow the node
    # name into the entry title if it was renamed on-device.
    device = coordinator.device
    if device is not None:
        data_updates: dict[str, Any] = {}
        if device.device_id and not entry.data.get(CONF_DEVICE_ID):
            data_updates[CONF_DEVICE_ID] = device.device_id
        new_title = (
            device.node_name
            if device.node_name and device.node_name != entry.title
            else None
        )
        if new_title and entry.data.get(CONF_NODE) != device.node_name:
            # Follow the node into entry data too, so a later reauth
            # (which reads CONF_NODE, falling back to the title) shows
            # the current name rather than the stale pre-rename one.
            data_updates[CONF_NODE] = device.node_name
        if data_updates or new_title:
            hass.config_entries.async_update_entry(
                entry,
                data={**entry.data, **data_updates} if data_updates else entry.data,
                title=new_title or entry.title,
            )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def _async_options_updated(hass: HomeAssistant, entry: PlaiiinLightConfigEntry) -> None:
    """Reload the entry when options (poll interval) change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: PlaiiinLightConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
