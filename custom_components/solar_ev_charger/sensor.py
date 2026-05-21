"""Sensor platform for Solar EV Charger integration."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
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
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SolarEVChargerStatusSensor(coordinator)])

class SolarEVChargerStatusSensor(CoordinatorEntity, SensorEntity):
    """Sensor to display the charging status."""

    def __init__(self, coordinator: SolarEVChargerCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_name = "Solar EV Charger Status"
        self._attr_unique_id = f"{coordinator.entry.entry_id}_status"

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        if not self.coordinator.enabled:
            return "Disabled"
        if not self.coordinator.solar_only_mode:
            return "Manual"
        return "Solar Only"
