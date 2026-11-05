"""Scene entities: one per scene saved on the lamp (firmware 2.6.0+).

Activating one applies the lamp's own scene (POST /api/scenes/<name>/activate).
Scenes are made and edited in the PlaiiinLight apps; the list here follows the
lamp's (new scenes appear, deleted ones are removed) as the coordinator
re-reads it.
"""
from __future__ import annotations

from typing import Any

from homeassistant.components.scene import Scene
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
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
    """Add a scene entity per lamp scene, and keep the set in step."""
    coordinator = entry.runtime_data
    known: dict[str, PlaiiinLightScene] = {}

    @callback
    def _sync() -> None:
        names = coordinator.scenes or []
        new = [n for n in names if n not in known]
        for name in new:
            known[name] = PlaiiinLightScene(coordinator, name)
        if new:
            async_add_entities([known[n] for n in new])
        # Deleted on the lamp (or the scene list is gone): drop the entity.
        registry = er.async_get(hass)
        for name in [n for n in known if n not in names]:
            entity = known.pop(name)
            if entity.entity_id and registry.async_get(entity.entity_id):
                registry.async_remove(entity.entity_id)

    _sync()
    entry.async_on_unload(coordinator.async_add_listener(_sync))


class PlaiiinLightScene(CoordinatorEntity[PlaiiinLightCoordinator], Scene):
    """One of the lamp's scenes."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: PlaiiinLightCoordinator, name: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        lamp_id = entry.unique_id or entry.entry_id
        self._scene = name
        self._attr_name = name
        self._attr_unique_id = f"{lamp_id}_scene_{name}"
        # Same identifiers as the light, so the scenes sit on the lamp's device.
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, lamp_id)})

    async def async_activate(self, **kwargs: Any) -> None:
        try:
            await self.coordinator.client.activate_scene(self._scene)
        except LamposError as err:
            raise HomeAssistantError(f"Scene failed: {err}") from err
        await self.coordinator.async_request_refresh()
