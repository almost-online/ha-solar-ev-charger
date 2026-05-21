"""Switch platform for Solar EV Charger integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SolarEVChargerCoordinator

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        SolarEVChargerEnableSwitch(coordinator),
        SolarEVChargerSolarOnlySwitch(coordinator),
    ])

class SolarEVChargerEnableSwitch(CoordinatorEntity, SwitchEntity):
    """Switch to enable/disable the integration logic."""

    def __init__(self, coordinator: SolarEVChargerCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_name = "Solar EV Charger Enabled"
        self._attr_unique_id = f"{coordinator.entry.entry_id}_enabled"

    @property
    def is_on(self) -> bool:
        """Return True if the switch is on."""
        return self.coordinator.enabled

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        self.coordinator.enabled = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        self.coordinator.enabled = False
        self.async_write_ha_state()

class SolarEVChargerSolarOnlySwitch(CoordinatorEntity, SwitchEntity):
    """Switch to enable/disable solar-only mode."""

    def __init__(self, coordinator: SolarEVChargerCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_name = "Solar EV Charger Solar Only Mode"
        self._attr_unique_id = f"{coordinator.entry.entry_id}_solar_only"

    @property
    def is_on(self) -> bool:
        """Return True if the switch is on."""
        return self.coordinator.solar_only_mode

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        self.coordinator.solar_only_mode = True
        self.async_write_ha_state()
        await self.coordinator.calculate_and_set_current()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        self.coordinator.solar_only_mode = False
        self.async_write_ha_state()
