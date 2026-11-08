"""Tests for the scene select (the lamp's active scene)."""
from homeassistant.components.select import (
    ATTR_OPTION,
    SERVICE_SELECT_OPTION,
)
from homeassistant.components.select import (
    DOMAIN as SELECT_DOMAIN,
)
from homeassistant.const import ATTR_ENTITY_ID, STATE_UNKNOWN

from .conftest import STATE_JSON, mock_lamp_api, setup_entry

ENTITY = "select.plaiiinlight_tower_scene"


def calls_to(aioclient_mock, method, path):
    return [c for c in aioclient_mock.mock_calls if c[0] == method and c[1].path == path]


async def test_options_are_the_lamp_scenes(hass, aioclient_mock, config_entry):
    mock_lamp_api(aioclient_mock)
    await setup_entry(hass, config_entry)
    state = hass.states.get(ENTITY)
    assert state is not None
    assert state.attributes["options"] == ["evening", "reading"]
    # No "scene" in /api/state (older firmware) or none active: no option.
    assert state.state == STATE_UNKNOWN


async def test_current_option_is_the_active_scene(hass, aioclient_mock, config_entry):
    mock_lamp_api(aioclient_mock, state={**STATE_JSON, "scene": "reading"})
    await setup_entry(hass, config_entry)
    assert hass.states.get(ENTITY).state == "reading"


async def test_scene_that_ended_clears_the_option(hass, aioclient_mock, config_entry):
    mock_lamp_api(aioclient_mock, state={**STATE_JSON, "scene": "reading"})
    await setup_entry(hass, config_entry)
    aioclient_mock.clear_requests()
    mock_lamp_api(aioclient_mock, state={**STATE_JSON, "scene": None})
    await config_entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY).state == STATE_UNKNOWN


async def test_selecting_activates_the_scene(hass, aioclient_mock, config_entry):
    mock_lamp_api(aioclient_mock)
    await setup_entry(hass, config_entry)
    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: ENTITY, ATTR_OPTION: "evening"},
        blocking=True,
    )
    assert len(calls_to(aioclient_mock, "POST", "/api/scenes/evening/activate")) == 1


async def test_old_firmware_has_no_scene_select(hass, aioclient_mock, config_entry):
    mock_lamp_api(aioclient_mock, scenes_status=404)
    await setup_entry(hass, config_entry)
    assert hass.states.get(ENTITY) is None
