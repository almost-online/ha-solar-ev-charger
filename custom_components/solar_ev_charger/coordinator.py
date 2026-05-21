"""Coordinator for Solar EV Charger integration."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_SET_VALUE
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    DOMAIN,
    CONF_SOLAR_POWER_ENTITY,
    CONF_CONSUMPTION_POWER_ENTITY,
    CONF_GRID_POWER_ENTITY,
    CONF_BATTERY_POWER_ENTITY,
    CONF_BATTERY_SOC_ENTITY,
    CONF_EV_CHARGER_POWER_ENTITY,
    CONF_EV_CHARGER_CONTROL_CURRENT_ENTITY,
    CONF_EV_CHARGER_MAX_CURRENT,
)

_LOGGER = logging.getLogger(__name__)

class SolarEVChargerCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data and controlling EV charger."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
        )
        self.entry = entry
        self.enabled = True
        self.solar_only_mode = True

        self.entities = {
            "solar": entry.data[CONF_SOLAR_POWER_ENTITY],
            "consumption": entry.data[CONF_CONSUMPTION_POWER_ENTITY],
            "grid": entry.data[CONF_GRID_POWER_ENTITY],
            "battery_power": entry.data.get(CONF_BATTERY_POWER_ENTITY),
            "battery_soc": entry.data.get(CONF_BATTERY_SOC_ENTITY),
            "ev_power": entry.data[CONF_EV_CHARGER_POWER_ENTITY],
            "ev_control": entry.data[CONF_EV_CHARGER_CONTROL_CURRENT_ENTITY],
        }
        self.max_current = entry.data[CONF_EV_CHARGER_MAX_CURRENT]

        # Track state changes
        for entity_id in self.entities.values():
            if entity_id:
                async_track_state_change_event(
                    self.hass, [entity_id], self._async_handle_state_change
                )

    async def _async_handle_state_change(self, event):
        """Handle state changes of tracked entities."""
        await self.calculate_and_set_current()

    async def _async_update_data(self):
        """Update data via library."""
        # This is where we could poll if needed, 
        # but we mainly rely on state changes.
        return {}

    def get_state_val(self, entity_id: str) -> float:
        """Get float value of entity state."""
        if not entity_id:
            return 0.0
        state = self.hass.states.get(entity_id)
        if state is None or state.state in ("unknown", "unavailable"):
            return 0.0
        try:
            return float(state.state)
        except ValueError:
            return 0.0

    async def calculate_and_set_current(self):
        """Calculate required current and set it on the charger."""
        if not self.enabled or not self.solar_only_mode:
            return

        solar_power = self.get_state_val(self.entities["solar"])
        consumption_power = self.get_state_val(self.entities["consumption"])
        grid_power = self.get_state_val(self.entities["grid"])
        ev_power = self.get_state_val(self.entities["ev_power"])
        
        # Grid power: positive = export (surplus), negative = import (from grid)
        # Based on user description: Grid Pover entity (export/import as positive/negative power)
        
        # Total available power for EV = EV Power + Grid Power (if positive)
        # Or more simply: surplus = grid_power
        # If grid_power > 0, we have surplus.
        # If grid_power < 0, we are importing.
        
        # Current EV charging current (estimated from power if not available, 
        # but we have the control entity)
        control_entity = self.entities["ev_control"]
        current_setpoint = self.get_state_val(control_entity)

        # Assumptions: 
        # 230V single phase or 3-phase. 
        # Let's assume 230V and we adjust Amps.
        # P = V * I * phases
        # For simplicity, let's use the power surplus to adjust Amps.
        
        voltage = 230.0 # Could be made configurable
        phases = 1 # Could be made configurable
        
        # surplus_power = grid_power
        # If battery_power is positive (charging), it is also "surplus" that could go to the car
        # If battery_power is negative (discharging), it is house consumption
        battery_power = self.get_state_val(self.entities["battery_power"])
        
        # surplus = export to grid + power going to battery
        surplus_power = grid_power + max(0, battery_power)
        
        # Calculate how much we can change the current
        # delta_I = surplus_power / (voltage * phases)
        change_amps = surplus_power / (voltage * phases)
        
        new_setpoint = current_setpoint + change_amps
        
        # Clamp new_setpoint
        if new_setpoint > self.max_current:
            new_setpoint = float(self.max_current)
        if new_setpoint < 0:
            new_setpoint = 0.0
            
        # Optimization: only set if change is significant (e.g. > 0.5A)
        if abs(new_setpoint - current_setpoint) >= 0.5 or (new_setpoint == 0 and current_setpoint > 0):
            _LOGGER.info("Adjusting EV charger current from %s to %s", current_setpoint, new_setpoint)
            await self.hass.services.async_call(
                "number",
                SERVICE_SET_VALUE,
                {
                    ATTR_ENTITY_ID: control_entity,
                    "value": round(new_setpoint, 1),
                },
            )
