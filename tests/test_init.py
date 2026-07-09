"""Tests for config entry setup and unload."""
import aiohttp
from homeassistant.config_entries import ConfigEntryState

from .conftest import BASE, mock_lamp_api, setup_entry


async def test_setup_and_unload(hass, aioclient_mock, config_entry):
    mock_lamp_api(aioclient_mock)
    await setup_entry(hass, config_entry)
    assert config_entry.state is ConfigEntryState.LOADED
    coordinator = config_entry.runtime_data
    assert coordinator.device.led_count == 4
    assert coordinator.device.node_name == "plaiiinlight-tower"
    assert coordinator.effects == ["aurora", "sparkle"]
    assert coordinator.data.on is True

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.NOT_LOADED


async def test_setup_retry_when_unreachable(hass, aioclient_mock, config_entry):
    aioclient_mock.get(f"{BASE}/api", exc=aiohttp.ClientError("unreachable"))
    await setup_entry(hass, config_entry)
    assert config_entry.state is ConfigEntryState.SETUP_RETRY
