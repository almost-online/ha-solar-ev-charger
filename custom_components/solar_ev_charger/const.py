"""Constants for the Solar EV Charger integration."""

DOMAIN = "solar_ev_charger"

CONF_SOLAR_POWER_ENTITY = "solar_power_entity"
CONF_CONSUMPTION_POWER_ENTITY = "consumption_power_entity"
CONF_GRID_POWER_ENTITY = "grid_power_entity"
CONF_BATTERY_POWER_ENTITY = "battery_power_entity"
CONF_BATTERY_SOC_ENTITY = "battery_soc_entity"
CONF_EV_CHARGER_POWER_ENTITY = "ev_charger_power_entity"
CONF_EV_CHARGER_CONTROL_CURRENT_ENTITY = "ev_charger_control_current_entity"
CONF_EV_CHARGER_MAX_CURRENT = "ev_charger_max_current"
CONF_EV_CHARGER_MAX_CURRENT_ENTITY = "ev_charger_max_current_entity"
CONF_EV_CHARGER_VOLTAGE = "ev_charger_voltage"
CONF_EV_CHARGER_VOLTAGE_ENTITY = "ev_charger_voltage_entity"
CONF_MIN_BATTERY_SOC = "min_battery_soc"
CONF_SMOOTHING_PERIOD = "smoothing_period"

DEFAULT_NAME = "Solar EV Charger"
DEFAULT_VOLTAGE = 230
DEFAULT_MIN_BATTERY_SOC = 90
DEFAULT_SMOOTHING_PERIOD = 30
