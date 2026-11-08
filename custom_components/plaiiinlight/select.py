"""Scene select: which of the lamp's scenes is showing, and a way to pick one.

The options are the scenes saved on the lamp (firmware 2.6.0+). The current
option is the scene the lamp reports as active (firmware 2.6.1+, "scene" in
GET /api/state): it follows activations from the apps, from Home Assistant
and from swarm peers, and is empty once something else takes over the lamp.
Picking an option activates that scene. Lamps without scenes get no select.
"""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import LamposError
from .const import DOMAIN
from .coordinator import PlaiiinLightConfigEntry, PlaiiinLightCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PlaiiinLightConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add the scene select once the lamp is known to have scenes."""
    coordinator = entry.runtime_data
    added = False

    @callback
    def _sync() -> None:
        nonlocal added
        if not added and coordinator.scenes is not None:
            added = True
            async_add_entities([PlaiiinLightSceneSelect(coordinator)])

    _sync()
    entry.async_on_unload(coordinator.async_add_listener(_sync))


class PlaiiinLightSceneSelect(CoordinatorEntity[PlaiiinLightCoordinator], SelectEntity):
    """The lamp's active scene."""

    _attr_has_entity_name = True
    _attr_translation_key = "scene"
    _attr_icon = "mdi:image-multiple"

    def __init__(self, coordinator: PlaiiinLightCoordinator) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        lamp_id = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{lamp_id}_scene_select"
        # Same identifiers as the light, so it sits on the lamp's device.
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, lamp_id)})

    @property
    def options(self) -> list[str]:
        return list(self.coordinator.scenes or [])

    @property
    def current_option(self) -> str | None:
        state = self.coordinator.data
        scene = state.scene if state is not None else None
        return scene if scene in self.options else None

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.scenes is not None

    async def async_select_option(self, option: str) -> None:
        try:
            await self.coordinator.client.activate_scene(option)
        except LamposError as err:
            raise HomeAssistantError(f"Scene failed: {err}") from err
        await self.coordinator.async_request_refresh()
