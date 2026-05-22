"""Number platform for Solar EV Charger integration."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    CONF_EV_CHARGER_MAX_CURRENT,
    CONF_MIN_BATTERY_SOC,
    CONF_SMOOTHING_PERIOD,
)
from .coordinator import SolarEVChargerCoordinator

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the number platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        SolarEVChargerMaxCurrentNumber(coordinator),
        SolarEVChargerMinBatterySOCNumber(coordinator),
        SolarEVChargerSmoothingPeriodNumber(coordinator),
    ])

class SolarEVChargerMaxCurrentNumber(CoordinatorEntity, NumberEntity):
    """Number entity to control max charging current."""

    def __init__(self, coordinator: SolarEVChargerCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_name = "Solar EV Charger Max Current"
        self._attr_unique_id = f"{coordinator.entry.entry_id}_max_current"
        self._attr_device_info = coordinator.device_info
        self._attr_native_min_value = 0.0
        self._attr_native_max_value = 32.0
        self._attr_native_step = 0.1
        self._attr_native_unit_of_measurement = "A"

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return float(self.coordinator.max_current)

    async def async_set_native_value(self, value: float) -> None:
        """Update the value."""
        self.coordinator.max_current = value
        self.async_write_ha_state()
        await self.coordinator.calculate_and_set_current()

class SolarEVChargerMinBatterySOCNumber(CoordinatorEntity, NumberEntity):
    """Number entity to control minimum battery SOC."""

    def __init__(self, coordinator: SolarEVChargerCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_name = "Solar EV Charger Min Battery SOC"
        self._attr_unique_id = f"{coordinator.entry.entry_id}_min_battery_soc"
        self._attr_device_info = coordinator.device_info
        self._attr_native_min_value = 0.0
        self._attr_native_max_value = 100.0
        self._attr_native_step = 1.0
        self._attr_native_unit_of_measurement = "%"

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return float(self.coordinator.min_battery_soc)

    async def async_set_native_value(self, value: float) -> None:
        """Update the value."""
        self.coordinator.min_battery_soc = value
        self.async_write_ha_state()
        await self.coordinator.calculate_and_set_current()

class SolarEVChargerSmoothingPeriodNumber(CoordinatorEntity, NumberEntity):
    """Number entity to control smoothing period."""

    def __init__(self, coordinator: SolarEVChargerCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_name = "Solar EV Charger Smoothing Period"
        self._attr_unique_id = f"{coordinator.entry.entry_id}_smoothing_period"
        self._attr_device_info = coordinator.device_info
        self._attr_native_min_value = 0.0
        self._attr_native_max_value = 300.0
        self._attr_native_step = 1.0
        self._attr_native_unit_of_measurement = "s"

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return float(self.coordinator.smoothing_period)

    async def async_set_native_value(self, value: float) -> None:
        """Update the value."""
        self.coordinator.smoothing_period = value
        self.async_write_ha_state()
        await self.coordinator.calculate_and_set_current()
