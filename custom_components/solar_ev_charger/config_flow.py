"""Config flow for Solar EV Charger integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

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
    CONF_EV_CHARGER_VOLTAGE,
    CONF_EV_CHARGER_VOLTAGE_ENTITY,
    CONF_MIN_BATTERY_SOC,
    CONF_SMOOTHING_PERIOD,
    DEFAULT_VOLTAGE,
    DEFAULT_MIN_BATTERY_SOC,
    DEFAULT_SMOOTHING_PERIOD,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SOLAR_POWER_ENTITY): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="power")
        ),
        vol.Required(CONF_CONSUMPTION_POWER_ENTITY): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="power")
        ),
        vol.Required(CONF_GRID_POWER_ENTITY): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="power")
        ),
        vol.Optional(CONF_BATTERY_POWER_ENTITY): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="power")
        ),
        vol.Optional(CONF_BATTERY_SOC_ENTITY): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="battery")
        ),
        vol.Required(CONF_EV_CHARGER_POWER_ENTITY): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="power")
        ),
        vol.Required(CONF_EV_CHARGER_CONTROL_CURRENT_ENTITY): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="number")
        ),
        vol.Required(CONF_EV_CHARGER_MAX_CURRENT, default=16): vol.Coerce(int),
        vol.Optional(CONF_EV_CHARGER_VOLTAGE_ENTITY): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="voltage")
        ),
        vol.Optional(CONF_EV_CHARGER_VOLTAGE, default=DEFAULT_VOLTAGE): vol.Coerce(int),
        vol.Optional(CONF_MIN_BATTERY_SOC, default=DEFAULT_MIN_BATTERY_SOC): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=100)
        ),
        vol.Optional(CONF_SMOOTHING_PERIOD, default=DEFAULT_SMOOTHING_PERIOD): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=300)
        ),
    }
)


@config_entries.HANDLERS.register(DOMAIN)
class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Solar EV Charger."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        return self.async_create_entry(title="Solar EV Charger", data=user_input)
