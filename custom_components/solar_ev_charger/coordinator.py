"""Coordinator for Solar EV Charger integration."""
from __future__ import annotations

import logging
import math
import time
from collections import deque
from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_SET_VALUE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    DOMAIN,
    DEFAULT_NAME,
    CONF_SOLAR_POWER_ENTITY,
    CONF_CONSUMPTION_POWER_ENTITY,
    CONF_GRID_POWER_ENTITY,
    CONF_BATTERY_POWER_ENTITY,
    CONF_BATTERY_SOC_ENTITY,
    CONF_EV_CHARGER_POWER_ENTITY,
    CONF_EV_CHARGER_CONTROL_CURRENT_ENTITY,
    CONF_EV_CHARGER_MAX_CURRENT,
    CONF_EV_CHARGER_VOLTAGE,
    CONF_EV_CHARGER_VOLTAGE_ENTITY,
    CONF_MIN_BATTERY_SOC,
    CONF_SMOOTHING_PERIOD,
    DEFAULT_VOLTAGE,
    DEFAULT_MIN_BATTERY_SOC,
    DEFAULT_SMOOTHING_PERIOD,
)

# Battery/charger proportions
HIGH_HALF_SOC = 0.9  # 10/90%
LOW_HALF_SOC = 0.6   # 40/60%

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
            "voltage_entity": entry.data.get(CONF_EV_CHARGER_VOLTAGE_ENTITY),
        }
        self.max_current = entry.data[CONF_EV_CHARGER_MAX_CURRENT]
        self.default_voltage = entry.data.get(CONF_EV_CHARGER_VOLTAGE, DEFAULT_VOLTAGE)
        self.min_battery_soc = entry.data.get(CONF_MIN_BATTERY_SOC, DEFAULT_MIN_BATTERY_SOC)
        self.smoothing_period = entry.data.get(CONF_SMOOTHING_PERIOD, DEFAULT_SMOOTHING_PERIOD)

        self._last_update_time = datetime.min
        self._power_history = deque()

        self.device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=DEFAULT_NAME,
            manufacturer="Solar EV Charger",
            model="Solar Optimization",
        )

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

    def _get_smoothed_power(self, raw_power: float) -> float:
        """Get smoothed power using a rolling average over the smoothing period."""
        now = time.time()
        self._power_history.append((now, raw_power))

        # Evict old data points
        while self._power_history and (now - self._power_history[0][0] > self.smoothing_period):
            self._power_history.popleft()

        if not self._power_history:
            return raw_power

        return sum(val for _, val in self._power_history) / len(self._power_history)

    async def calculate_and_set_current(self):
        """Calculate required current and set it on the charger."""
        if not self.enabled or not self.solar_only_mode:
            return

        grid_power = self.get_state_val(self.entities["grid"])
        ev_power = self.get_state_val(self.entities["ev_power"])
        battery_soc = self.get_state_val(self.entities["battery_soc"])

        # 1. Hard cutoff guardrail: If battery is strictly below minimum config, KILL EV charging
        if self.entities["battery_soc"] and battery_soc < self.min_battery_soc:
            _LOGGER.debug("Battery SOC %s < %s. Stopping EV charging.", battery_soc, self.min_battery_soc)
            await self._set_charger_current(0)
            return

        # 2. Determine voltage dynamically or fall back to default configuration
        voltage = self.get_state_val(self.entities["voltage_entity"])
        if voltage <= 0:
            voltage = float(self.default_voltage)
        phases = 1

        # 3. Calculate 100% of raw excess physical power currently available
        # (-grid_power handles negative export correctly, adding current ev_power avoids loops)
        raw_excess = (-grid_power) + ev_power
        total_excess_power = self._get_smoothed_power(raw_excess)

        # 4. Calculate Linear Interpolation for EV Share
        # Lower boundary: min_battery_soc -> 60% (0.6)
        # Upper boundary: 95% SoC -> 90% (0.9)
        low_share = 0.6
        high_share = 0.9
        upper_soc_limit = 95.0

        if not self.entities["battery_soc"]:
            ev_share = 1.0  # No battery tracking, use all surplus
        elif battery_soc >= upper_soc_limit:
            ev_share = high_share
        elif battery_soc <= self.min_battery_soc:
            ev_share = low_share
        else:
            # Linear scale between min_battery_soc and 95%
            soc_range = upper_soc_limit - self.min_battery_soc
            ev_share = low_share + (
                (high_share - low_share) * (battery_soc - self.min_battery_soc) / soc_range
            )

        # 5. Allocate the power segment to the EV
        ev_allocated_power = total_excess_power * ev_share

        # 6. Convert Power to Target Amps
        target_amps = ev_allocated_power / (voltage * phases)

        # 7. Apply strict physical boundary limits
        MIN_CHARGE_AMPS = 6.0  # IEC 61851 minimum standard threshold

        if target_amps > self.max_current:
            new_control_amps = float(self.max_current)
        elif target_amps < MIN_CHARGE_AMPS:
            new_control_amps = 0.0
        else:
            # Use math.floor to be safe and slightly conservative against grid pulling
            new_control_amps = float(math.floor(target_amps))

        await self._set_charger_current(new_control_amps, battery_soc)

    async def _set_charger_current(self, new_setpoint: float, battery_soc: float | None = None):
        """Set the charger current with smoothing and deadband logic."""
        control_entity = self.entities["ev_control"]
        current_setpoint = self.get_state_val(control_entity)

        now = datetime.now()
        time_diff = (now - self._last_update_time).total_seconds()

        # Immediate stop or start from zero ignores smoothing period
        is_immediate = (new_setpoint == 0 and current_setpoint > 0) or (new_setpoint > 0 and current_setpoint == 0)

        if not is_immediate and time_diff < self.smoothing_period:
            _LOGGER.debug("Smoothing: skipping update. Last update was %s seconds ago.", time_diff)
            return

        # Apply 0.5A deadband unless it's a start/stop
        if not is_immediate and abs(new_setpoint - current_setpoint) < 0.5:
            return

        _LOGGER.info("Adjusting EV charger current from %s to %s (SOC: %s%%)",
                     current_setpoint, new_setpoint, battery_soc)
        self._last_update_time = now
        await self.hass.services.async_call(
            "number",
            SERVICE_SET_VALUE,
            {
                ATTR_ENTITY_ID: control_entity,
                "value": round(new_setpoint, 1),
            },
        )
