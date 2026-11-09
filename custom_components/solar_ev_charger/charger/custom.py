"""Custom charger: any power sensor plus a `number` current entity."""
from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.const import ATTR_ENTITY_ID

from ..const import (
    CONF_EV_CHARGER_CONTROL_CURRENT_ENTITY,
    CONF_EV_CHARGER_POWER_ENTITY,
    MIN_CHARGE_AMPS,
)
from .base import ChargerDriver

# SERVICE_SET_VALUE is not in homeassistant.const in some versions,
# and the number component defines it as 'set_value'
SERVICE_SET_VALUE = "set_value"

_LOGGER = logging.getLogger(__name__)


class CustomChargerDriver(ChargerDriver):
    """Writes the target current to a user-selected `number` entity."""

    def __init__(self, coordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        data = coordinator.entry.data
        self._power_entity = data[CONF_EV_CHARGER_POWER_ENTITY]
        self.control_entity = data[CONF_EV_CHARGER_CONTROL_CURRENT_ENTITY]
        self._last_update_time = datetime.min

    @property
    def power_entity(self) -> str | None:
        return self._power_entity

    @property
    def tracked_entities(self) -> list[str]:
        return [*super().tracked_entities, self.control_entity]

    async def async_apply(self, target_amps, battery_soc, battery_power) -> None:
        await self._set_charger_current(target_amps, battery_soc)

    async def _set_charger_current(self, new_setpoint: float, battery_soc: float | None = None):
        """Set the charger current with smoothing and deadband logic."""
        control_entity = self.control_entity
        current_setpoint = self.coordinator.get_state_val(control_entity)

        now = datetime.now()
        time_diff = (now - self._last_update_time).total_seconds()

        # Immediate stop or start from zero ignores smoothing period
        is_immediate = (new_setpoint == 0 and current_setpoint > 0) or (
                new_setpoint > 0 and current_setpoint == 0)

        if not is_immediate and time_diff < self.coordinator.smoothing_period:
            _LOGGER.debug("Smoothing: skipping update. Last update was %s seconds ago.", time_diff)
            return

        # Apply 0.5A deadband unless it's a start/stop
        if not is_immediate and abs(new_setpoint - current_setpoint) <= 0.5:
            return

        if new_setpoint <= 0:
            new_setpoint = MIN_CHARGE_AMPS

        _LOGGER.info("Adjusting EV charger current from %s to %s (SOC: %s%%)",
                     current_setpoint, new_setpoint, battery_soc)
        self._last_update_time = now
        try:
            await self.hass.services.async_call(
                "number",
                SERVICE_SET_VALUE,
                {
                    ATTR_ENTITY_ID: control_entity,
                    "value": round(new_setpoint, 1),
                },
                blocking=True,
            )
        except Exception as err:
            if new_setpoint == 0:
                _LOGGER.debug("Failed to set charger current to 0, "
                              "it might not be supported by the entity: %s", err)
            else:
                _LOGGER.error("Error setting charger current: %s", err)

            await self._set_charger_current(MIN_CHARGE_AMPS, battery_soc)
