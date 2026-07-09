"""Tests for the lamp HTTP client."""
import aiohttp
import pytest
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.plaiiinlight.api import (
    LamposAuthError,
    LamposClient,
    LamposConnectionError,
)

from .conftest import BASE, DEVICE_JSON, HOST, JS_JSON, STATE_JSON, WHOAMI_USER


def make_client(hass, share_key=None):
    return LamposClient(async_get_clientsession(hass), HOST, share_key=share_key)


async def test_get_state(hass, aioclient_mock):
    aioclient_mock.get(f"{BASE}/api/state", json=STATE_JSON)
    state = await make_client(hass).get_state()
    assert state.on is True
    assert state.color == (255, 0, 0)
    assert state.mode == "api"
    assert state.brightness == 128
    assert state.current is None


async def test_get_device(hass, aioclient_mock):
    aioclient_mock.get(f"{BASE}/api", json=DEVICE_JSON)
    device = await make_client(hass).get_device()
    assert device.node_name == "plaiiinlight-tower"
    assert device.led_count == 4
    assert device.lamp_form == "tower"
    assert device.firmware_version == "1.9.10"
    assert device.vendor == "plaiiin"


async def test_share_key_sends_bearer_header(hass, aioclient_mock):
    aioclient_mock.get(f"{BASE}/api/whoami", json=WHOAMI_USER)
    whoami = await make_client(hass, share_key="PLK-test").get_whoami()
    assert whoami.role == "user"
    assert whoami.paired is True
    headers = aioclient_mock.mock_calls[0][3]
    assert headers["Authorization"] == "Bearer PLK-test"


async def test_no_auth_header_without_key(hass, aioclient_mock):
    aioclient_mock.get(f"{BASE}/api/whoami", json={"role": "admin", "paired": False})
    await make_client(hass).get_whoami()
    headers = aioclient_mock.mock_calls[0][3]
    assert not headers or "Authorization" not in headers


async def test_set_color_replicates_led_count(hass, aioclient_mock):
    aioclient_mock.post(f"{BASE}/api/color", json={"status": "ok"})
    await make_client(hass).set_color((0, 0, 255), 4)
    assert aioclient_mock.mock_calls[0][2] == {"colors": [[0, 0, 255]] * 4}


async def test_play_effect_posts_file(hass, aioclient_mock):
    aioclient_mock.post(f"{BASE}/api/play", json={"status": "ok"})
    await make_client(hass).play_effect("aurora")
    assert aioclient_mock.mock_calls[0][2] == {"file": "aurora"}


async def test_list_effects(hass, aioclient_mock):
    aioclient_mock.get(f"{BASE}/api/js", json=JS_JSON)
    assert await make_client(hass).list_effects() == ["aurora", "sparkle"]


async def test_set_power_and_brightness_and_mode(hass, aioclient_mock):
    aioclient_mock.post(f"{BASE}/api/power", json={"status": "ok"})
    aioclient_mock.post(f"{BASE}/api/brightness", json={"status": "ok"})
    aioclient_mock.put(f"{BASE}/api/mode", json={"status": "ok"})
    client = make_client(hass)
    await client.set_power(False)
    await client.set_brightness(200)
    await client.set_mode("api")
    payloads = [call[2] for call in aioclient_mock.mock_calls]
    assert {"on": False} in payloads
    assert {"brightness": 200} in payloads
    assert {"mode": "api"} in payloads


async def test_401_raises_auth_error(hass, aioclient_mock):
    aioclient_mock.get(f"{BASE}/api/state", status=401)
    with pytest.raises(LamposAuthError):
        await make_client(hass).get_state()


async def test_500_raises_connection_error(hass, aioclient_mock):
    aioclient_mock.get(f"{BASE}/api/state", status=500)
    with pytest.raises(LamposConnectionError):
        await make_client(hass).get_state()


async def test_network_error_raises_connection_error(hass, aioclient_mock):
    aioclient_mock.get(f"{BASE}/api/state", exc=aiohttp.ClientError("boom"))
    with pytest.raises(LamposConnectionError):
        await make_client(hass).get_state()


async def test_malformed_json_raises_connection_error(hass, aioclient_mock):
    aioclient_mock.get(f"{BASE}/api/state", text="not json")
    with pytest.raises(LamposConnectionError):
        await make_client(hass).get_state()


async def test_ipv6_host_is_bracketed_in_url(hass, aioclient_mock):
    aioclient_mock.get("http://[fd00::1]:80/api/state", json=STATE_JSON)
    client = LamposClient(async_get_clientsession(hass), "fd00::1")
    state = await client.get_state()
    assert state.on is True


async def test_set_color_with_unknown_led_count_raises_without_request(
    hass, aioclient_mock
):
    with pytest.raises(LamposConnectionError):
        await make_client(hass).set_color((1, 2, 3), 0)
    assert not aioclient_mock.mock_calls
