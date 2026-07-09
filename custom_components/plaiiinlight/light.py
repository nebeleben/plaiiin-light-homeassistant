"""Light entity for a PlaiiinLightOS lamp."""
from __future__ import annotations

from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_EFFECT,
    ATTR_HS_COLOR,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util.color import color_hs_to_RGB, color_RGB_to_hs

from .api import LamposError
from .const import DOMAIN, EFFECT_SOLID, MODE_API
from .coordinator import PlaiiinLightConfigEntry, PlaiiinLightCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PlaiiinLightConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the lamp's light entity."""
    async_add_entities([PlaiiinLightLight(entry.runtime_data)])


class PlaiiinLightLight(CoordinatorEntity[PlaiiinLightCoordinator], LightEntity):
    """The lamp as a HomeAssistant light."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_color_mode = ColorMode.HS
    _attr_supported_color_modes = {ColorMode.HS}
    _attr_supported_features = LightEntityFeature.EFFECT

    def __init__(self, coordinator: PlaiiinLightCoordinator) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        device = coordinator.device
        self._attr_unique_id = entry.unique_id or entry.entry_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._attr_unique_id)},
            name=entry.title,
            manufacturer=device.vendor if device else "plaiiin",
            model=device.lamp_form if device else None,
            sw_version=device.firmware_version if device else None,
        )

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.on

    @property
    def brightness(self) -> int:
        return self.coordinator.data.brightness

    @property
    def hs_color(self) -> tuple[float, float]:
        return color_RGB_to_hs(*self.coordinator.data.color)

    @property
    def effect_list(self) -> list[str]:
        return [EFFECT_SOLID, *self.coordinator.effects]

    @property
    def effect(self) -> str | None:
        state = self.coordinator.data
        if state.mode == MODE_API:
            return EFFECT_SOLID
        if state.mode == "js":
            return state.current
        return None  # "stream": externally driven, no named effect

    async def async_turn_on(self, **kwargs: Any) -> None:
        client = self.coordinator.client
        state = self.coordinator.data
        effect: str | None = kwargs.get(ATTR_EFFECT)
        hs: tuple[float, float] | None = kwargs.get(ATTR_HS_COLOR)
        brightness: int | None = kwargs.get(ATTR_BRIGHTNESS)
        try:
            if not state.on:
                await client.set_power(True)
            if effect == EFFECT_SOLID:
                await client.set_mode(MODE_API)
            elif effect is not None:
                await client.play_effect(effect)
            if hs is not None:
                # Color only sets the lamp's baseColor — never the mode. A
                # running effect keeps playing; selecting the "Solid" effect
                # is the explicit way to show the color full-screen.
                await client.set_color(
                    color_hs_to_RGB(*hs), self.coordinator.device.led_count
                )
            if brightness is not None:
                await client.set_brightness(brightness)
        except LamposError as err:
            raise HomeAssistantError(f"Lamp command failed: {err}") from err
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        try:
            await self.coordinator.client.set_power(False)
        except LamposError as err:
            raise HomeAssistantError(f"Lamp command failed: {err}") from err
        await self.coordinator.async_request_refresh()
