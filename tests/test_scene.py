"""Tests for the scene entities."""
from homeassistant.components.scene import DOMAIN as SCENE_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_TURN_ON
from homeassistant.helpers import entity_registry as er

from custom_components.plaiiinlight.coordinator import SCENE_REFRESH_POLLS

from .conftest import mock_lamp_api, setup_entry


def calls_to(aioclient_mock, method, path):
    return [c for c in aioclient_mock.mock_calls if c[0] == method and c[1].path == path]


async def test_one_entity_per_lamp_scene(hass, aioclient_mock, config_entry):
    mock_lamp_api(aioclient_mock)
    await setup_entry(hass, config_entry)
    assert hass.states.get("scene.plaiiinlight_tower_evening") is not None
    assert hass.states.get("scene.plaiiinlight_tower_reading") is not None


async def test_activate_applies_the_lamp_scene(hass, aioclient_mock, config_entry):
    mock_lamp_api(aioclient_mock)
    await setup_entry(hass, config_entry)
    await hass.services.async_call(
        SCENE_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: "scene.plaiiinlight_tower_evening"},
        blocking=True,
    )
    assert len(calls_to(aioclient_mock, "POST", "/api/scenes/evening/activate")) == 1


async def test_old_firmware_has_no_scenes(hass, aioclient_mock, config_entry):
    mock_lamp_api(aioclient_mock, scenes_status=404)
    await setup_entry(hass, config_entry)
    # The light still works; there are just no scene entities.
    assert hass.states.get("light.plaiiinlight_tower") is not None
    assert not [e for e in hass.states.async_entity_ids(SCENE_DOMAIN)]


async def test_scene_list_follows_the_lamp(hass, aioclient_mock, config_entry):
    mock_lamp_api(aioclient_mock)
    await setup_entry(hass, config_entry)
    coordinator = config_entry.runtime_data

    aioclient_mock.clear_requests()
    mock_lamp_api(
        aioclient_mock,
        scenes={"scenes": [{"name": "evening", "scene": {}}, {"name": "party", "scene": {}}]},
    )
    for _ in range(SCENE_REFRESH_POLLS):
        await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert hass.states.get("scene.plaiiinlight_tower_party") is not None
    registry = er.async_get(hass)
    assert registry.async_get("scene.plaiiinlight_tower_reading") is None
    assert hass.states.get("scene.plaiiinlight_tower_evening") is not None
