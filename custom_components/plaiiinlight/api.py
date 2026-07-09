"""Async HTTP client for the PlaiiinLightOS lamp API.

Deliberately self-contained (session injected, no Home Assistant imports)
so it can later be extracted to a PyPI package for an HA-core submission.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import aiohttp

DEFAULT_TIMEOUT = 3.0


class LamposError(Exception):
    """Base error for lamp communication."""


class LamposConnectionError(LamposError):
    """Lamp unreachable, timed out, or returned an unexpected status."""


class LamposAuthError(LamposError):
    """Share key missing, invalid, or revoked (HTTP 401/403)."""


@dataclass(slots=True)
class LampState:
    """Mirror of GET /api/state."""

    on: bool
    color: tuple[int, int, int]
    mode: str
    brightness: int
    current: str | None


@dataclass(slots=True)
class LampDevice:
    """Subset of GET /api used by the integration."""

    node_name: str
    led_count: int
    lamp_form: str
    firmware_version: str
    vendor: str


@dataclass(slots=True)
class WhoAmI:
    """Mirror of GET /api/whoami."""

    role: str
    paired: bool


class LamposClient:
    """Minimal client for the lamp endpoints the integration uses."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        port: int = 80,
        share_key: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self._session = session
        self._base = f"http://{host}:{port}"
        self._share_key = share_key
        self._timeout = timeout

    async def _request(
        self, method: str, path: str, json: dict[str, Any] | None = None
    ) -> Any:
        headers = {}
        if self._share_key:
            headers["Authorization"] = f"Bearer {self._share_key}"
        try:
            async with asyncio.timeout(self._timeout):
                resp = await self._session.request(
                    method, f"{self._base}{path}", json=json, headers=headers
                )
                if resp.status in (401, 403):
                    raise LamposAuthError(f"{path} returned {resp.status}")
                if resp.status >= 400:
                    raise LamposConnectionError(f"{path} returned {resp.status}")
                try:
                    return await resp.json(content_type=None)
                except ValueError as err:
                    raise LamposConnectionError(
                        f"{path}: invalid JSON response"
                    ) from err
        except (aiohttp.ClientError, TimeoutError, OSError) as err:
            raise LamposConnectionError(f"{path}: {err}") from err

    async def get_state(self) -> LampState:
        data = await self._request("GET", "/api/state")
        color = data.get("color") or [0, 0, 0]
        return LampState(
            on=bool(data.get("on")),
            color=(int(color[0]), int(color[1]), int(color[2])),
            mode=str(data.get("mode", "api")),
            brightness=int(data.get("brightness", 0)),
            current=data.get("current") or None,
        )

    async def get_device(self) -> LampDevice:
        data = await self._request("GET", "/api")
        return LampDevice(
            node_name=str(data.get("nodeName", "")),
            led_count=int(data.get("ledCount", 0)),
            lamp_form=str(data.get("lampForm", "")),
            firmware_version=str(data.get("firmwareVersion", "")),
            vendor=str(data.get("vendor", "")),
        )

    async def get_whoami(self) -> WhoAmI:
        data = await self._request("GET", "/api/whoami")
        return WhoAmI(role=str(data.get("role", "none")), paired=bool(data.get("paired")))

    async def set_power(self, on: bool) -> None:
        await self._request("POST", "/api/power", json={"on": on})

    async def set_brightness(self, brightness: int) -> None:
        await self._request("POST", "/api/brightness", json={"brightness": brightness})

    async def set_color(self, rgb: tuple[int, int, int], led_count: int) -> None:
        await self._request("POST", "/api/color", json={"colors": [list(rgb)] * led_count})

    async def set_mode(self, mode: str) -> None:
        await self._request("PUT", "/api/mode", json={"mode": mode})

    async def list_effects(self) -> list[str]:
        data = await self._request("GET", "/api/js")
        return [str(name) for name in data.get("scripts", [])]

    async def play_effect(self, name: str) -> None:
        await self._request("POST", "/api/play", json={"file": name})
