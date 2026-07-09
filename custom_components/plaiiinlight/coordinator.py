"""Polling coordinator for a PlaiiinLightOS lamp."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    LampDevice,
    LamposAuthError,
    LamposClient,
    LamposConnectionError,
    LampState,
)
from .const import CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

type PlaiiinLightConfigEntry = ConfigEntry[PlaiiinLightCoordinator]


class PlaiiinLightCoordinator(DataUpdateCoordinator[LampState]):
    """Polls GET /api/state; holds device info and the effect list."""

    config_entry: PlaiiinLightConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: PlaiiinLightConfigEntry,
        client: LamposClient,
    ) -> None:
        interval = entry.options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {entry.title}",
            update_interval=timedelta(seconds=interval),
        )
        self.client = client
        self.device: LampDevice | None = None
        self.effects: list[str] = []

    async def _async_setup(self) -> None:
        try:
            self.device = await self.client.get_device()
            self.effects = await self.client.list_effects()
        except LamposAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except LamposConnectionError as err:
            raise UpdateFailed(str(err)) from err

    async def _async_update_data(self) -> LampState:
        try:
            return await self.client.get_state()
        except LamposAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except LamposConnectionError as err:
            raise UpdateFailed(str(err)) from err
