"""Placeholder config flow handler.

HA core requires a `ConfigFlow` registered for `DOMAIN` before it will set up
*any* config entry for an integration whose manifest declares
`config_flow: true` (see `ConfigEntry.async_setup`, which unconditionally
imports the `config_flow` platform and looks up a registered flow handler for
the entry's domain). This is a minimal stand-in with no steps implemented;
the real user/reauth/options flows are built out in a later task.
"""
from __future__ import annotations

from homeassistant.config_entries import ConfigFlow

from .const import DOMAIN


class PlaiiinLightConfigFlow(ConfigFlow, domain=DOMAIN):
    """Placeholder config flow; steps are implemented in a later task."""

    VERSION = 1
