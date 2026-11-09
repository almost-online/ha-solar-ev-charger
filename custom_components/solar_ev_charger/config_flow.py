"""Config flow for Solar EV Charger integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .charger.solax import SOLAX_DOMAIN, resolve_solax_entities
from .const import (
    DOMAIN,
    CONF_SOLAR_POWER_ENTITY,
    CONF_CONSUMPTION_POWER_ENTITY,
    CONF_GRID_POWER_ENTITY,
    CONF_BATTERY_POWER_ENTITY,
    CONF_BATTERY_SOC_ENTITY,
    CONF_CHARGER_TYPE,
    CONF_CHARGER_DEVICE,
    CONF_EV_CHARGER_POWER_ENTITY,
    CONF_EV_CHARGER_CONTROL_CURRENT_ENTITY,
    CONF_EV_CHARGER_MAX_CURRENT,
    CONF_EV_CHARGER_VOLTAGE,
    CONF_EV_CHARGER_VOLTAGE_ENTITY,
    CONF_MIN_BATTERY_SOC,
    CONF_MAX_BATTERY_DISCHARGE_POWER,
    CONF_SMOOTHING_PERIOD,
    CHARGER_TYPE_SOLAX_MODBUS,
    CHARGER_TYPES,
    DEFAULT_CHARGER_TYPE,
    DEFAULT_VOLTAGE,
    DEFAULT_MIN_BATTERY_SOC,
    DEFAULT_MAX_BATTERY_DISCHARGE_POWER,
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
        vol.Required(CONF_CHARGER_TYPE, default=DEFAULT_CHARGER_TYPE): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=CHARGER_TYPES,
                translation_key=CONF_CHARGER_TYPE,
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        ),
        vol.Required(CONF_EV_CHARGER_MAX_CURRENT, default=16): vol.Coerce(int),
        vol.Optional(CONF_EV_CHARGER_VOLTAGE_ENTITY): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="voltage")
        ),
        vol.Optional(CONF_EV_CHARGER_VOLTAGE, default=DEFAULT_VOLTAGE): vol.Coerce(int),
        vol.Optional(CONF_MIN_BATTERY_SOC, default=DEFAULT_MIN_BATTERY_SOC): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=100)
        ),
        vol.Optional(CONF_MAX_BATTERY_DISCHARGE_POWER, default=DEFAULT_MAX_BATTERY_DISCHARGE_POWER / 1000.0): vol.All(
            vol.Coerce(float), vol.Range(min=0)
        ),
        vol.Optional(CONF_SMOOTHING_PERIOD, default=DEFAULT_SMOOTHING_PERIOD): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=300)
        ),
    }
)

STEP_CUSTOM_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EV_CHARGER_POWER_ENTITY): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="power")
        ),
        vol.Required(CONF_EV_CHARGER_CONTROL_CURRENT_ENTITY): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="number")
        ),
    }
)

STEP_SOLAX_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CHARGER_DEVICE): selector.DeviceSelector(
            selector.DeviceSelectorConfig(integration=SOLAX_DOMAIN)
        ),
    }
)


def _discharge_to_watts(user_input: dict[str, Any]) -> dict[str, Any]:
    """Convert the kW form value to watts for storage."""
    if CONF_MAX_BATTERY_DISCHARGE_POWER in user_input:
        user_input[CONF_MAX_BATTERY_DISCHARGE_POWER] = user_input[CONF_MAX_BATTERY_DISCHARGE_POWER] * 1000.0
    return user_input


@config_entries.HANDLERS.register(DOMAIN)
class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Solar EV Charger."""

    VERSION = 2

    def __init__(self) -> None:
        """Initialize."""
        self._data: dict[str, Any] = {}
        self._reconfigure_entry: config_entries.ConfigEntry | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        self._data = _discharge_to_watts(user_input)
        return await self._async_step_charger()

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the reconfigure step."""
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        self._reconfigure_entry = entry

        if user_input is not None:
            self._data = {**entry.data, **_discharge_to_watts(user_input)}
            return await self._async_step_charger()

        # Convert W to kW for suggested values
        suggested_values = entry.data.copy()
        if CONF_MAX_BATTERY_DISCHARGE_POWER in suggested_values:
            suggested_values[CONF_MAX_BATTERY_DISCHARGE_POWER] = suggested_values[CONF_MAX_BATTERY_DISCHARGE_POWER] / 1000.0

        schema = self.add_suggested_values_to_schema(STEP_USER_DATA_SCHEMA, suggested_values)

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=schema,
        )

    async def _async_step_charger(self) -> FlowResult:
        """Continue with the step for the selected charger type."""
        if self._data.get(CONF_CHARGER_TYPE) == CHARGER_TYPE_SOLAX_MODBUS:
            return await self.async_step_solax_modbus()
        return await self.async_step_custom()

    async def async_step_custom(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Pick the power sensor and current `number` of a custom charger."""
        if user_input is not None:
            return self._async_finish(user_input)

        return self.async_show_form(
            step_id="custom",
            data_schema=self.add_suggested_values_to_schema(STEP_CUSTOM_DATA_SCHEMA, self._data),
        )

    async def async_step_solax_modbus(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Pick a Solax ModBus EV charger device."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if resolve_solax_entities(self.hass, user_input[CONF_CHARGER_DEVICE]) is None:
                errors["base"] = "solax_entities_not_found"
            else:
                return self._async_finish(user_input)

        return self.async_show_form(
            step_id="solax_modbus",
            data_schema=self.add_suggested_values_to_schema(STEP_SOLAX_DATA_SCHEMA, self._data),
            errors=errors,
        )

    def _async_finish(self, charger_input: dict[str, Any]) -> FlowResult:
        """Create or update the entry with the charger step data."""
        data = {**self._data, **charger_input}
        if self._reconfigure_entry is not None:
            return self.async_update_reload_and_abort(self._reconfigure_entry, data=data)
        return self.async_create_entry(title="Solar EV Charger", data=data)
