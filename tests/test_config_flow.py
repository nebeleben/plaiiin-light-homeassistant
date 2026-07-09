"""Tests for the config flow."""
import aiohttp
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.data_entry_flow import FlowResultType

from custom_components.plaiiinlight.const import CONF_NODE, CONF_SHARE_KEY, DOMAIN

from .conftest import (
    BASE,
    DEVICE_JSON,
    HOST,
    NODE,
    WHOAMI_NONE,
    WHOAMI_UNPAIRED,
    WHOAMI_USER,
    mock_lamp_api,
)


async def start_user_flow(hass):
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )


async def test_user_flow_unclaimed_lamp(hass, aioclient_mock):
    mock_lamp_api(aioclient_mock)  # whoami: admin, unpaired
    result = await start_user_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: HOST, CONF_PORT: 80}
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == NODE
    assert result["data"] == {CONF_HOST: HOST, CONF_PORT: 80, CONF_NODE: NODE}
    assert result["result"].unique_id == NODE


async def test_user_flow_paired_lamp_asks_share_key(hass, aioclient_mock):
    mock_lamp_api(aioclient_mock, whoami=WHOAMI_NONE)
    result = await start_user_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: HOST, CONF_PORT: 80}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "share_key"

    aioclient_mock.clear_requests()
    mock_lamp_api(aioclient_mock, whoami=WHOAMI_USER)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_SHARE_KEY: "PLK-abc"}
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_SHARE_KEY] == "PLK-abc"


async def test_user_flow_rejected_share_key_shows_error(hass, aioclient_mock):
    mock_lamp_api(aioclient_mock, whoami=WHOAMI_NONE)
    result = await start_user_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: HOST, CONF_PORT: 80}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_SHARE_KEY: "PLK-bad"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "share_key"
    assert result["errors"] == {"base": "invalid_share_key"}


async def test_user_flow_cannot_connect(hass, aioclient_mock):
    aioclient_mock.get(f"{BASE}/api", exc=aiohttp.ClientError("boom"))
    result = await start_user_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: HOST, CONF_PORT: 80}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_duplicate_aborts_and_updates_host(
    hass, aioclient_mock, config_entry
):
    config_entry.add_to_hass(hass)
    new_base = "http://192.168.1.99:80"
    aioclient_mock.get(f"{new_base}/api", json=DEVICE_JSON)
    aioclient_mock.get(f"{new_base}/api/whoami", json=WHOAMI_UNPAIRED)
    result = await start_user_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: "192.168.1.99", CONF_PORT: 80}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert config_entry.data[CONF_HOST] == "192.168.1.99"
