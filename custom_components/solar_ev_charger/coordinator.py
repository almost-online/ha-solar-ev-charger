"""Coordinator for Solar EV Charger integration."""
from __future__ import annotations

import logging
import math
import time
from collections import deque
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .charger import create_driver
from .const import (
    DOMAIN,
    DEFAULT_NAME,
    CONF_SOLAR_POWER_ENTITY,
    CONF_CONSUMPTION_POWER_ENTITY,
    CONF_GRID_POWER_ENTITY,
    CONF_BATTERY_POWER_ENTITY,
    CONF_BATTERY_SOC_ENTITY,
    CONF_CHARGER_TYPE,
    CONF_EV_CHARGER_MAX_CURRENT,
    CONF_EV_CHARGER_VOLTAGE,
    CONF_EV_CHARGER_VOLTAGE_ENTITY,
    CONF_MIN_BATTERY_SOC,
    CONF_MAX_BATTERY_DISCHARGE_POWER,
    CONF_SMOOTHING_PERIOD,
    DEFAULT_CHARGER_TYPE,
    DEFAULT_VOLTAGE,
    DEFAULT_MIN_BATTERY_SOC,
    DEFAULT_MAX_BATTERY_DISCHARGE_POWER,
    DEFAULT_SMOOTHING_PERIOD,
    MIN_CHARGE_AMPS,
)

# Battery/charger proportions
HIGH_SHARE_SOC = 0.9  # 10/90%
LOW_SHARE_SOC = 0.6  # 40/60%

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
        self.ignore_battery_charging = False

        self.max_current = entry.data[CONF_EV_CHARGER_MAX_CURRENT]
        self.default_voltage = entry.data.get(CONF_EV_CHARGER_VOLTAGE, DEFAULT_VOLTAGE)
        self.min_battery_soc = entry.data.get(CONF_MIN_BATTERY_SOC, DEFAULT_MIN_BATTERY_SOC)
        self.max_battery_discharge_power = entry.data.get(
            CONF_MAX_BATTERY_DISCHARGE_POWER, DEFAULT_MAX_BATTERY_DISCHARGE_POWER
        )
        self.smoothing_period = entry.data.get(CONF_SMOOTHING_PERIOD, DEFAULT_SMOOTHING_PERIOD)

        self.charger_type = entry.data.get(CONF_CHARGER_TYPE, DEFAULT_CHARGER_TYPE)
        self.driver = create_driver(self)

        self.entities = {
            "solar": entry.data[CONF_SOLAR_POWER_ENTITY],
            "consumption": entry.data[CONF_CONSUMPTION_POWER_ENTITY],
            "grid": entry.data[CONF_GRID_POWER_ENTITY],
            "battery_power": entry.data.get(CONF_BATTERY_POWER_ENTITY),
            "battery_soc": entry.data.get(CONF_BATTERY_SOC_ENTITY),
            "ev_power": self.driver.power_entity,
            "voltage_entity": entry.data.get(CONF_EV_CHARGER_VOLTAGE_ENTITY)
            or self.driver.voltage_entity,
        }

        self._power_history = deque()

        self.device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=DEFAULT_NAME,
            manufacturer="Solar EV Charger",
            model="Solar Optimization",
        )

        # Track state changes
        tracked = {e for e in (*self.entities.values(), *self.driver.tracked_entities) if e}
        for entity_id in tracked:
            async_track_state_change_event(
                self.hass, [entity_id], self._async_handle_state_change
            )

    @callback
    def _async_handle_state_change(self, event):
        """Handle state changes of tracked entities."""
        self.hass.async_create_task(self._async_process_state_change())

    async def _async_process_state_change(self):
        """Process state changes asynchronously."""
        self.async_set_updated_data(await self._async_update_data())
        await self.calculate_and_set_current()

    async def _async_update_data(self):
        """Update data for the coordinator."""
        return {
            "solar": self.get_state_val(self.entities["solar"]),
            "solar_entity": self.entities["solar"],
            "consumption": self.get_state_val(self.entities["consumption"]),
            "consumption_entity": self.entities["consumption"],
            "grid": self.get_state_val(self.entities["grid"]),
            "grid_entity": self.entities["grid"],
            "battery_power": self.get_state_val(self.entities["battery_power"]),
            "battery_power_entity": self.entities["battery_power"],
            "battery_soc": self.get_state_val(self.entities["battery_soc"]),
            "battery_soc_entity": self.entities["battery_soc"],
            "ev_power": self.get_state_val(self.entities["ev_power"]),
            "ev_power_entity": self.entities["ev_power"],
            "voltage": self.get_state_val(self.entities["voltage_entity"]) or float(
                self.default_voltage),
            "voltage_entity": self.entities["voltage_entity"],
            "max_current": self.max_current,
            "min_battery_soc": self.min_battery_soc,
            "max_battery_discharge_power": self.max_battery_discharge_power,
            "smoothing_period": self.smoothing_period,
            "charger_type": self.charger_type,
            **self.driver.extra_attributes,
        }

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
        consumption_power = self.get_state_val(self.entities["consumption"])
        ev_power = self.get_state_val(self.entities["ev_power"])
        battery_soc = self.get_state_val(self.entities["battery_soc"])
        battery_power = self.get_state_val(self.entities["battery_power"])
        solar_power = self.get_state_val(self.entities["solar"])

        soc_for_driver = battery_soc if self.entities["battery_soc"] else None
        power_for_driver = battery_power if self.entities["battery_power"] else None

        # 1. Hard cutoff guardrail: If battery is strictly below minimum config, KILL EV charging
        if (
            self.driver.stop_below_min_soc
            and self.entities["battery_soc"]
            and battery_soc < self.min_battery_soc
        ):
            _LOGGER.debug("Battery SOC %s < %s. Stopping EV charging.", battery_soc,
                          self.min_battery_soc)
            await self.driver.async_apply(0, soc_for_driver, power_for_driver)
            return

        # 2. Determine voltage dynamically or fall back to default configuration
        voltage = self.get_state_val(self.entities["voltage_entity"])
        if voltage <= 0:
            voltage = float(self.default_voltage)
        phases = 1

        # 3. Calculate raw excess physical power currently available
        # Equation: (-grid_power) + ev_power + battery_power
        # battery_power is positive for charging, negative for discharging.
        # So adding it adds charging power to the pool and adding discharging power (negative) subtracts from the pool.
        raw_available = (-grid_power) + ev_power + battery_power

        # Apply battery discharge limit for EV charging
        # If battery is discharging (battery_power < 0), we want to limit how much of that discharge
        # is used for the EV. 
        # The user wants to limit battery discharge to max_battery_discharge_power.
        # Current logic: raw_available = (-grid) + ev_power + battery_power.
        # If solar=0, consumption=1kW, grid=0.5kW, battery=-0.5kW (discharging), ev_power=0.
        # Then raw_available = -0.5 + 0 + (-0.5) = -1.0kW.
        # The equation for available power is essentially: solar_power - consumption_power + battery_discharge_limit
        # grid_power = consumption_power + ev_power - solar_power - battery_power_discharging
        # (-grid_power) + ev_power + battery_power = -(consumption + ev - solar - battery_power) + ev + battery_power
        # = -consumption - ev + solar + battery_power + ev + battery_power = solar - consumption + 2*battery_power? No.
        
        # Let's use: raw_available = solar_power - consumption_power + battery_discharge_limit
        # battery_power in this system: positive=charging, negative=discharging.
        # So raw_available = solar_power - consumption_power + min(abs(battery_power_discharging), limit) ? No, that's also not quite it.

        # User example: solar=0.5, consumption=1, limit=2. EV should be max 1.5.
        # solar - consumption + limit = 0.5 - 1 + 2 = 1.5. Correct!

        raw_available = solar_power - consumption_power + self.max_battery_discharge_power

        total_available_power = self._get_smoothed_power(raw_available)

        # 4. Calculate Linear Interpolation for EV Share
        upper_soc_limit = (100 + self.min_battery_soc) / 2

        # If ignore_battery_charging is enabled, EV takes 100% of available power
        if self.ignore_battery_charging:
            ev_share = 1.0
        elif not battery_soc:
            ev_share = 1.0  # No battery tracking, use all surplus
        elif battery_soc >= upper_soc_limit:
            ev_share = HIGH_SHARE_SOC
        elif battery_soc <= self.min_battery_soc:
            ev_share = LOW_SHARE_SOC
        else:
            # Linear scale between min_battery_soc and 95%
            soc_range = upper_soc_limit - self.min_battery_soc
            ev_share = max(LOW_SHARE_SOC + (
                    (HIGH_SHARE_SOC - LOW_SHARE_SOC) * (
                    battery_soc - self.min_battery_soc) / soc_range
            ), 1)

        # 5. Allocate the power segment to the EV
        ev_allocated_power = total_available_power * ev_share

        # 7. Convert Power to Target Amps
        target_amps = ev_allocated_power / (voltage * phases)

        # 8. Apply strict physical boundary limits
        if target_amps < MIN_CHARGE_AMPS:
            new_control_amps = 0
        elif target_amps > self.max_current:
            new_control_amps = float(self.max_current)
        else:
            # Use math.floor to be safe and slightly conservative against grid pulling
            new_control_amps = float(math.floor(target_amps))

        await self.driver.async_apply(new_control_amps, soc_for_driver, power_for_driver)
