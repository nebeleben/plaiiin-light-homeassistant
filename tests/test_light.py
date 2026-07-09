"""Tests for the light entity."""
import aiohttp
import pytest
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_EFFECT,
    ATTR_EFFECT_LIST,
    ATTR_HS_COLOR,
)
from homeassistant.components.light import (
    DOMAIN as LIGHT_DOMAIN,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_ON,
)
from homeassistant.exceptions import HomeAssistantError

from .conftest import BASE, STATE_JSON, mock_lamp_api, setup_entry

ENTITY = "light.plaiiinlight_tower"


def calls_to(aioclient_mock, path):
    """All mocked requests whose URL path matches."""
    return [call for call in aioclient_mock.mock_calls if call[1].path == path]


async def turn_on(hass, **kwargs):
    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: ENTITY, **kwargs},
        blocking=True,
    )


async def test_state_mapping(hass, aioclient_mock, config_entry):
    mock_lamp_api(aioclient_mock)
    await setup_entry(hass, config_entry)
    state = hass.states.get(ENTITY)
    assert state is not None
    assert state.state == STATE_ON
    assert state.attributes[ATTR_BRIGHTNESS] == 128
    assert state.attributes[ATTR_HS_COLOR] == (0.0, 100.0)
    assert state.attributes[ATTR_EFFECT] == "Solid"
    assert state.attributes[ATTR_EFFECT_LIST] == ["Solid", "aurora", "sparkle"]


async def test_js_mode_reports_running_effect(hass, aioclient_mock, config_entry):
    mock_lamp_api(aioclient_mock, state={**STATE_JSON, "mode": "js", "current": "aurora"})
    await setup_entry(hass, config_entry)
    assert hass.states.get(ENTITY).attributes[ATTR_EFFECT] == "aurora"


async def test_turn_off(hass, aioclient_mock, config_entry):
    mock_lamp_api(aioclient_mock)
    await setup_entry(hass, config_entry)
    await hass.services.async_call(
        LIGHT_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: ENTITY}, blocking=True
    )
    assert calls_to(aioclient_mock, "/api/power")[-1][2] == {"on": False}


async def test_turn_on_powers_on_when_off(hass, aioclient_mock, config_entry):
    mock_lamp_api(aioclient_mock, state={**STATE_JSON, "on": False})
    await setup_entry(hass, config_entry)
    await turn_on(hass)
    assert calls_to(aioclient_mock, "/api/power")[-1][2] == {"on": True}


async def test_color_from_js_mode_never_changes_mode(hass, aioclient_mock, config_entry):
    """A color write only sets the base color — a running effect keeps playing."""
    mock_lamp_api(aioclient_mock, state={**STATE_JSON, "mode": "js", "current": "aurora"})
    await setup_entry(hass, config_entry)
    await turn_on(hass, **{ATTR_HS_COLOR: (240.0, 100.0)})
    assert calls_to(aioclient_mock, "/api/color")[-1][2] == {"colors": [[0, 0, 255]] * 4}
    assert not calls_to(aioclient_mock, "/api/mode")


async def test_brightness_from_js_mode_never_changes_mode(hass, aioclient_mock, config_entry):
    mock_lamp_api(aioclient_mock, state={**STATE_JSON, "mode": "js", "current": "aurora"})
    await setup_entry(hass, config_entry)
    await turn_on(hass, **{ATTR_BRIGHTNESS: 42})
    assert calls_to(aioclient_mock, "/api/brightness")[-1][2] == {"brightness": 42}
    assert not calls_to(aioclient_mock, "/api/mode")


async def test_color_in_api_mode_skips_mode_call(hass, aioclient_mock, config_entry):
    mock_lamp_api(aioclient_mock)
    await setup_entry(hass, config_entry)
    await turn_on(hass, **{ATTR_HS_COLOR: (240.0, 100.0)})
    assert not calls_to(aioclient_mock, "/api/mode")
    assert calls_to(aioclient_mock, "/api/color")[-1][2] == {"colors": [[0, 0, 255]] * 4}


async def test_select_effect_plays_script(hass, aioclient_mock, config_entry):
    mock_lamp_api(aioclient_mock)
    await setup_entry(hass, config_entry)
    await turn_on(hass, **{ATTR_EFFECT: "aurora"})
    assert calls_to(aioclient_mock, "/api/play")[-1][2] == {"file": "aurora"}
    assert not calls_to(aioclient_mock, "/api/mode")


async def test_select_solid_switches_mode(hass, aioclient_mock, config_entry):
    mock_lamp_api(aioclient_mock, state={**STATE_JSON, "mode": "js", "current": "aurora"})
    await setup_entry(hass, config_entry)
    await turn_on(hass, **{ATTR_EFFECT: "Solid"})
    assert calls_to(aioclient_mock, "/api/mode")[-1][2] == {"mode": "api"}
    assert not calls_to(aioclient_mock, "/api/play")


async def test_set_brightness(hass, aioclient_mock, config_entry):
    mock_lamp_api(aioclient_mock)
    await setup_entry(hass, config_entry)
    await turn_on(hass, **{ATTR_BRIGHTNESS: 255})
    assert calls_to(aioclient_mock, "/api/brightness")[-1][2] == {"brightness": 255}


async def test_effect_with_color_plays_and_sets_base_color(hass, aioclient_mock, config_entry):
    """Effect and color in one call: play the effect, set the base color."""
    mock_lamp_api(aioclient_mock, state={**STATE_JSON, "mode": "js", "current": "sparkle"})
    await setup_entry(hass, config_entry)
    await turn_on(hass, **{ATTR_EFFECT: "aurora", ATTR_HS_COLOR: (240.0, 100.0)})
    assert calls_to(aioclient_mock, "/api/play")[-1][2] == {"file": "aurora"}
    assert calls_to(aioclient_mock, "/api/color")
    assert not calls_to(aioclient_mock, "/api/mode")


async def test_failed_write_raises_and_skips_refresh(hass, aioclient_mock, config_entry):
    """A lamp error surfaces as HomeAssistantError and no refresh follows."""
    mock_lamp_api(aioclient_mock)
    await setup_entry(hass, config_entry)
    # First-registered matcher wins in AiohttpClientMocker: re-register with
    # the failing power endpoint ahead of the working mocks.
    aioclient_mock.clear_requests()
    aioclient_mock.post(f"{BASE}/api/power", exc=aiohttp.ClientError("boom"))
    mock_lamp_api(aioclient_mock)
    state_calls_before = len(calls_to(aioclient_mock, "/api/state"))
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            LIGHT_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: ENTITY}, blocking=True
        )
    await hass.async_block_till_done()
    assert len(calls_to(aioclient_mock, "/api/state")) == state_calls_before
