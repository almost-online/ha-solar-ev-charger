"""Solax ModBus EV charger (`solax_modbus` integration)."""
from __future__ import annotations

import logging
import time
from typing import Any

from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import entity_registry as er

from ..const import CONF_CHARGER_DEVICE, MIN_CHARGE_AMPS
from .base import ChargerDriver
from .solax_policy import SolaxStartStopPolicy

_LOGGER = logging.getLogger(__name__)

SOLAX_DOMAIN = "solax_modbus"

# solax_modbus unique ids are f"{platform_name}_{key}".
KEY_USE_MODE = "charger_use_mode"
SOLAX_ENTITY_KEYS = {
    "use_mode": ("select", KEY_USE_MODE),
    "current": ("number", "charge_current"),
    "power": ("sensor", "charge_power"),
    "voltage": ("sensor", "charge_voltage"),
    "run_mode": ("sensor", "run_mode"),
}
REQUIRED_KEYS = ("use_mode", "current")

MODE_STOP = "Stop"
MODE_FAST = "Fast"
ACTIVE_MODES = ("Fast", "ECO", "Green")

# Run Mode values that mean no car is plugged in or the charger can't charge.
NOT_CONNECTED_RUN_MODES = ("Available", "Unavailable", "Faulted", "Update")


def resolve_solax_entities(hass: HomeAssistant, device_id: str) -> dict[str, str] | None:
    """Find the charger entities of a solax_modbus device.

    Returns None when the device has no Charger Use Mode select or Charge Current number.
    """
    registry = er.async_get(hass)
    prefix = None
    for entry in er.async_entries_for_device(registry, device_id):
        if (
            entry.platform == SOLAX_DOMAIN
            and entry.domain == "select"
            and entry.unique_id.endswith(f"_{KEY_USE_MODE}")
        ):
            prefix = entry.unique_id[: -len(KEY_USE_MODE)]
            break
    if prefix is None:
        return None

    entities = {}
    for name, (domain, key) in SOLAX_ENTITY_KEYS.items():
        entity_id = registry.async_get_entity_id(domain, SOLAX_DOMAIN, f"{prefix}{key}")
        if entity_id:
            entities[name] = entity_id

    if any(key not in entities for key in REQUIRED_KEYS):
        return None
    return entities


class SolaxChargerDriver(ChargerDriver):
    """Switches Charger Use Mode between Fast and Stop and writes Charge Current."""

    stop_below_min_soc = False

    def __init__(self, coordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        device_id = coordinator.entry.data[CONF_CHARGER_DEVICE]
        entities = resolve_solax_entities(self.hass, device_id)
        if entities is None:
            raise ConfigEntryNotReady(
                f"Solax charger entities not found for device {device_id}"
            )
        self.entities = entities
        self.policy = SolaxStartStopPolicy(smoothing_period=coordinator.smoothing_period)
        self._last_current_change = 0.0

    @property
    def power_entity(self) -> str | None:
        return self.entities.get("power")

    @property
    def voltage_entity(self) -> str | None:
        return self.entities.get("voltage")

    @property
    def tracked_entities(self) -> list[str]:
        return list(self.entities.values())

    @property
    def extra_attributes(self) -> dict[str, Any]:
        return {
            "charger_use_mode": self._state(self.entities["use_mode"]),
            "charger_run_mode": self._state(self.entities.get("run_mode")),
            "battery_latch": self.policy.latched,
        }

    def _state(self, entity_id: str | None) -> str | None:
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        return state.state if state else None

    def _car_connected(self) -> bool:
        run_mode_entity = self.entities.get("run_mode")
        if not run_mode_entity:
            return True
        run_mode = self._state(run_mode_entity)
        if run_mode is None or run_mode in ("unknown", "unavailable"):
            return False
        return run_mode not in NOT_CONNECTED_RUN_MODES

    async def async_apply(self, target_amps, battery_soc, battery_power) -> None:
        if not self._car_connected():
            self.policy.reset_pending()
            return

        mode = self._state(self.entities["use_mode"])
        if mode is None or mode in ("unknown", "unavailable"):
            return
        active = mode in ACTIVE_MODES

        now = time.monotonic()
        self.policy.smoothing_period = self.coordinator.smoothing_period
        should_charge = self.policy.decide(
            now,
            active,
            target_amps,
            battery_soc,
            battery_power,
            self.coordinator.min_battery_soc,
        )

        if not should_charge:
            if active:
                _LOGGER.info(
                    "Stopping Solax charger (target %s A, SOC %s%%, battery %s W, latch %s)",
                    target_amps, battery_soc, battery_power, self.policy.latched,
                )
                await self._select_mode(MODE_STOP)
            return

        amps = min(max(target_amps, MIN_CHARGE_AMPS), float(self.coordinator.max_current))

        if mode != MODE_FAST:
            _LOGGER.info("Starting Solax charger in Fast mode at %s A (was %s)", amps, mode)
            await self._set_current(amps)
            await self._select_mode(MODE_FAST)
            self._last_current_change = now
            return

        current = self.coordinator.get_state_val(self.entities["current"])
        if now - self._last_current_change < self.coordinator.smoothing_period:
            return
        if abs(amps - current) <= 0.5:
            return

        _LOGGER.info("Adjusting Solax charger current from %s to %s (SOC: %s%%)",
                     current, amps, battery_soc)
        await self._set_current(amps)
        self._last_current_change = now

    async def _select_mode(self, option: str) -> None:
        try:
            await self.hass.services.async_call(
                "select",
                "select_option",
                {ATTR_ENTITY_ID: self.entities["use_mode"], "option": option},
                blocking=True,
            )
        except Exception as err:
            _LOGGER.error("Error setting Solax charger use mode to %s: %s", option, err)

    async def _set_current(self, amps: float) -> None:
        try:
            await self.hass.services.async_call(
                "number",
                "set_value",
                {ATTR_ENTITY_ID: self.entities["current"], "value": round(amps, 1)},
                blocking=True,
            )
        except Exception as err:
            _LOGGER.error("Error setting Solax charger current to %s A: %s", amps, err)
