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
    LamposNotFoundError,
    LampState,
)
from .const import CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

# The scene list changes rarely, and /api/scenes reads every scene document
# on the lamp: re-read it every SCENE_REFRESH_POLLS state polls, not each one.
SCENE_REFRESH_POLLS = 6

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
        # The lamp's scene names; None when the firmware has no scenes
        # (older than 2.6.0) or the list couldn't be read yet.
        self.scenes: list[str] | None = None
        self._polls_since_scenes = 0

    async def _async_setup(self) -> None:
        try:
            self.device = await self.client.get_device()
            self.effects = await self.client.list_effects()
            await self._refresh_scenes()
        except LamposAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except LamposConnectionError as err:
            raise UpdateFailed(str(err)) from err

    async def _refresh_scenes(self) -> None:
        """Re-read the scene names. A 404 means no scene support; any other
        failure keeps the last list (scenes are an extra, not worth failing
        the whole update for)."""
        self._polls_since_scenes = 0
        try:
            self.scenes = await self.client.list_scenes()
        except LamposNotFoundError:
            self.scenes = None
        except LamposAuthError:
            raise
        except LamposConnectionError as err:
            _LOGGER.debug("scene list unavailable: %s", err)

    async def _async_update_data(self) -> LampState:
        try:
            if self.device is None or not self.last_update_success:
                # Recovering from a prior failure (or first update after
                # setup never completed device/effects): the lamp may have
                # rebooted or its effect list may have changed while it was
                # unreachable, so refresh both before polling state.
                self.device = await self.client.get_device()
                self.effects = await self.client.list_effects()
                await self._refresh_scenes()
            else:
                self._polls_since_scenes += 1
                if self._polls_since_scenes >= SCENE_REFRESH_POLLS:
                    await self._refresh_scenes()
            return await self.client.get_state()
        except LamposAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except LamposConnectionError as err:
            raise UpdateFailed(str(err)) from err
