"""Sensor platform for Solar EV Charger integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfPower, UnitOfElectricPotential, PERCENTAGE
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
    
    entities = [SolarEVChargerStatusSensor(coordinator)]
    
    sensor_descriptions = [
        ("Solar Power", "solar", UnitOfPower.WATT, SensorDeviceClass.POWER),
        ("Consumption Power", "consumption", UnitOfPower.WATT, SensorDeviceClass.POWER),
        ("Grid Power", "grid", UnitOfPower.WATT, SensorDeviceClass.POWER),
        ("Battery Power", "battery_power", UnitOfPower.WATT, SensorDeviceClass.POWER),
        ("Battery SOC", "battery_soc", PERCENTAGE, SensorDeviceClass.BATTERY),
        ("EV Power", "ev_power", UnitOfPower.WATT, SensorDeviceClass.POWER),
        ("Voltage", "voltage", UnitOfElectricPotential.VOLT, SensorDeviceClass.VOLTAGE),
    ]
    
    for name, key, unit, device_class in sensor_descriptions:
        entities.append(SolarEVChargerDataSensor(coordinator, name, key, unit, device_class))
        
    async_add_entities(entities)

class SolarEVChargerStatusSensor(CoordinatorEntity, SensorEntity):
    """Sensor to display the charging status."""

    def __init__(self, coordinator: SolarEVChargerCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_name = "Solar EV Charger Status"
        self._attr_unique_id = f"{coordinator.entry.entry_id}_status"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        if not self.coordinator.enabled:
            return "Disabled"
        if not self.coordinator.solar_only_mode:
            return "Manual"
        if self.coordinator.ignore_battery_charging:
            return "Priority EV"
        return "Solar Only"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return self.coordinator.data

class SolarEVChargerDataSensor(CoordinatorEntity, SensorEntity):
    """Sensor to display data from the coordinator."""

    def __init__(
        self, 
        coordinator: SolarEVChargerCoordinator, 
        name: str, 
        key: str, 
        unit: str, 
        device_class: SensorDeviceClass
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._key = key
        self._attr_name = f"Solar EV Charger {name}"
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
        self._attr_device_info = coordinator.device_info
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        return self.coordinator.data.get(self._key)
