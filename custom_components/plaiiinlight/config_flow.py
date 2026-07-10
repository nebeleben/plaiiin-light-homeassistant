"""Config flow for the PlaiiinLight integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

try:
    from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo
except ImportError:
    # HA 2025.1 (our declared minimum): the helpers module only exists
    # since 2025.2 — fall back to the pre-move location.
    from homeassistant.components.zeroconf import ZeroconfServiceInfo

from .api import LamposClient, LamposError
from .const import (
    CONF_NODE,
    CONF_POLL_INTERVAL,
    CONF_SHARE_KEY,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_PORT,
    DOMAIN,
    MAX_POLL_INTERVAL,
    MIN_POLL_INTERVAL,
)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
    }
)
SHARE_KEY_SCHEMA = vol.Schema({vol.Required(CONF_SHARE_KEY): str})


class PlaiiinLightConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle manual and discovered lamp setup."""

    VERSION = 1

    def __init__(self) -> None:
        self._host: str | None = None
        self._port: int = DEFAULT_PORT
        self._node: str | None = None

    def _client(self, share_key: str | None = None) -> LamposClient:
        return LamposClient(
            async_get_clientsession(self.hass), self._host, self._port, share_key
        )

    def _entry_data(self, share_key: str | None = None) -> dict[str, Any]:
        data: dict[str, Any] = {
            CONF_HOST: self._host,
            CONF_PORT: self._port,
            CONF_NODE: self._node,
        }
        if share_key:
            data[CONF_SHARE_KEY] = share_key
        return data

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Manual add by host."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._host = user_input[CONF_HOST]
            self._port = user_input[CONF_PORT]
            try:
                device = await self._client().get_device()
                whoami = await self._client().get_whoami()
            except LamposError:
                errors["base"] = "cannot_connect"
            else:
                self._node = device.node_name
                await self.async_set_unique_id(self._node)
                self._abort_if_unique_id_configured(
                    updates={CONF_HOST: self._host, CONF_PORT: self._port}
                )
                if whoami.paired and whoami.role == "none":
                    return await self.async_step_share_key()
                return self.async_create_entry(title=self._node, data=self._entry_data())
        return self.async_show_form(
            step_id="user", data_schema=USER_SCHEMA, errors=errors
        )

    async def async_step_share_key(self, user_input: dict[str, Any] | None = None):
        """Ask for a share key on a claimed lamp; validate via whoami."""
        errors: dict[str, str] = {}
        if user_input is not None:
            key = user_input[CONF_SHARE_KEY]
            try:
                whoami = await self._client(key).get_whoami()
            except LamposError:
                errors["base"] = "cannot_connect"
            else:
                if whoami.role != "none":
                    return self.async_create_entry(
                        title=self._node, data=self._entry_data(key)
                    )
                errors["base"] = "invalid_share_key"
        return self.async_show_form(
            step_id="share_key",
            data_schema=SHARE_KEY_SCHEMA,
            description_placeholders={"name": self._node or ""},
            errors=errors,
        )

    async def async_step_zeroconf(self, discovery_info: ZeroconfServiceInfo):
        """A lamp announced itself via mDNS."""
        node = discovery_info.properties.get("node") or discovery_info.name.split(".")[0]
        self._host = discovery_info.host
        self._port = discovery_info.port or DEFAULT_PORT
        self._node = node
        await self.async_set_unique_id(node)
        self._abort_if_unique_id_configured(
            updates={CONF_HOST: self._host, CONF_PORT: self._port}
        )
        self.context["title_placeholders"] = {"name": node}
        if discovery_info.properties.get("paired") == "1":
            return await self.async_step_share_key()
        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ):
        """Confirm-only add for an unclaimed discovered lamp."""
        if user_input is not None:
            return self.async_create_entry(title=self._node, data=self._entry_data())
        self._set_confirm_only()
        return self.async_show_form(
            step_id="discovery_confirm",
            description_placeholders={"name": self._node or "", "host": self._host or ""},
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]):
        """Share key revoked, or an unclaimed lamp got claimed."""
        entry = self._get_reauth_entry()
        self._host = entry.data[CONF_HOST]
        self._port = entry.data.get(CONF_PORT, DEFAULT_PORT)
        self._node = entry.data.get(CONF_NODE, entry.title)
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ):
        """Ask for and validate a replacement share key."""
        errors: dict[str, str] = {}
        if user_input is not None:
            key = user_input[CONF_SHARE_KEY]
            try:
                whoami = await self._client(key).get_whoami()
            except LamposError:
                errors["base"] = "cannot_connect"
            else:
                if whoami.role != "none":
                    return self.async_update_reload_and_abort(
                        self._get_reauth_entry(),
                        data_updates={CONF_SHARE_KEY: key},
                    )
                errors["base"] = "invalid_share_key"
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=SHARE_KEY_SCHEMA,
            description_placeholders={"name": self._node or ""},
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Poll-interval options."""
        return PlaiiinLightOptionsFlow()


class PlaiiinLightOptionsFlow(OptionsFlow):
    """Options: poll interval."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_POLL_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL
                        ),
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_POLL_INTERVAL, max=MAX_POLL_INTERVAL),
                    ),
                }
            ),
        )
