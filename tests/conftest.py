"""Shared fixtures and lamp API mocks."""
from __future__ import annotations

from typing import Any

import pytest
from homeassistant.const import CONF_HOST, CONF_PORT
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.plaiiinlight.const import CONF_NODE, DOMAIN

HOST = "192.168.1.40"
BASE = f"http://{HOST}:80"
NODE = "plaiiinlight-tower"

DEVICE_JSON: dict[str, Any] = {
    "vendor": "plaiiin",
    "apiVersion": "1",
    "firmwareVersion": "1.9.10",
    "nodeName": NODE,
    "ledCount": 4,
    "lampForm": "tower",
    "lampType": "ws2812",
}
STATE_JSON: dict[str, Any] = {
    "on": True,
    "color": [255, 0, 0],
    "mode": "api",
    "brightness": 128,
    "current": None,
    "fps": 0,
}
JS_JSON: dict[str, Any] = {"scripts": ["aurora", "sparkle"], "playing": None}
WHOAMI_UNPAIRED = {"role": "admin", "paired": False}
WHOAMI_USER = {"role": "user", "paired": True}
WHOAMI_NONE = {"role": "none", "paired": True}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Allow loading the custom integration in every test."""
    yield


def mock_lamp_api(
    aioclient_mock: AiohttpClientMocker,
    state: dict[str, Any] | None = None,
    whoami: dict[str, Any] | None = None,
    js: dict[str, Any] | None = None,
) -> None:
    """Register the lamp's HTTP endpoints on the mocked session."""
    ok = {"status": "ok"}
    aioclient_mock.get(f"{BASE}/api", json=DEVICE_JSON)
    aioclient_mock.get(f"{BASE}/api/state", json=state or STATE_JSON)
    aioclient_mock.get(f"{BASE}/api/js", json=js or JS_JSON)
    aioclient_mock.get(f"{BASE}/api/whoami", json=whoami or WHOAMI_UNPAIRED)
    aioclient_mock.post(f"{BASE}/api/power", json=ok)
    aioclient_mock.post(f"{BASE}/api/brightness", json=ok)
    aioclient_mock.post(f"{BASE}/api/color", json=ok)
    aioclient_mock.put(f"{BASE}/api/mode", json=ok)
    aioclient_mock.post(f"{BASE}/api/play", json=ok)


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """A configured (unclaimed) lamp entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id=NODE,
        title=NODE,
        data={CONF_HOST: HOST, CONF_PORT: 80, CONF_NODE: NODE},
    )


async def setup_entry(hass, entry: MockConfigEntry) -> None:
    """Add the entry to hass and set it up."""
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
