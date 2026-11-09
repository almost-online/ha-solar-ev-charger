"""Config flow, migration and Solax driver tests. Need pytest-homeassistant-custom-component."""
from unittest.mock import AsyncMock, MagicMock

import pytest

pytest.importorskip("pytest_homeassistant_custom_component")

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_mock_service

from custom_components.solar_ev_charger.charger.custom import CustomChargerDriver
from custom_components.solar_ev_charger.charger.solax import SolaxChargerDriver
from custom_components.solar_ev_charger.const import DOMAIN

HOUSE = {
    "solar_power_entity": "sensor.solar",
    "consumption_power_entity": "sensor.consumption",
    "grid_power_entity": "sensor.grid",
    "battery_power_entity": "sensor.battery_power",
    "battery_soc_entity": "sensor.battery_soc",
}
LIMITS = {
    "ev_charger_max_current": 16,
    "ev_charger_voltage": 230,
    "min_battery_soc": 90,
    "max_battery_discharge_power": 1.0,
    "smoothing_period": 0,
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
def mock_http(hass):
    hass.http = MagicMock()
    hass.http.async_register_static_paths = AsyncMock()


def _solax_device(hass) -> str:
    solax_entry = MockConfigEntry(domain="solax_modbus")
    solax_entry.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=solax_entry.entry_id, identifiers={("solax_modbus", "evc")}
    )
    registry = er.async_get(hass)
    for domain, key, object_id in (
        ("select", "charger_use_mode", "garazh_use_mode"),
        ("number", "charge_current", "evc_charge_current"),
        ("number", "max_charge_current", "evc_max_charge_current"),
        ("sensor", "charge_power", "evc_charge_power"),
        ("sensor", "charge_voltage", "evc_charge_voltage"),
        ("sensor", "run_mode", "evc_run_mode"),
    ):
        registry.async_get_or_create(
            domain, "solax_modbus", f"EV Charger_{key}",
            device_id=device.id, suggested_object_id=object_id,
            config_entry=solax_entry,
        )
    return device.id


async def test_v1_entry_migrates_to_custom(hass, mock_http):
    entry = MockConfigEntry(
        domain=DOMAIN, version=1,
        data={**HOUSE, **LIMITS,
              "ev_charger_power_entity": "sensor.ev_power",
              "ev_charger_control_current_entity": "number.ev_current"},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.version == 2
    assert entry.data["charger_type"] == "custom"
    coordinator = hass.data[DOMAIN][entry.entry_id]
    assert isinstance(coordinator.driver, CustomChargerDriver)
    assert coordinator.entities["ev_power"] == "sensor.ev_power"


async def test_flow_solax(hass, mock_http):
    device_id = _solax_device(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**HOUSE, **LIMITS, "charger_type": "solax_modbus"}
    )
    assert result["step_id"] == "solax_modbus"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"charger_device": device_id}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["charger_device"] == device_id
    assert result["data"]["max_battery_discharge_power"] == 1000.0

    entry = result["result"]
    await hass.async_block_till_done()
    coordinator = hass.data[DOMAIN][entry.entry_id]
    assert isinstance(coordinator.driver, SolaxChargerDriver)
    assert coordinator.driver.entities["current"] == "number.evc_charge_current"
    assert coordinator.entities["ev_power"] == "sensor.evc_charge_power"
    assert coordinator.entities["voltage_entity"] == "sensor.evc_charge_voltage"


async def test_flow_custom(hass, mock_http):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**HOUSE, **LIMITS, "charger_type": "custom"}
    )
    assert result["step_id"] == "custom"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"ev_charger_power_entity": "sensor.ev_power",
         "ev_charger_control_current_entity": "number.ev_current"},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["charger_type"] == "custom"


async def test_solax_device_without_entities_errors(hass):
    solax_entry = MockConfigEntry(domain="solax_modbus")
    solax_entry.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=solax_entry.entry_id, identifiers={("solax_modbus", "inverter")}
    )
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**HOUSE, **LIMITS, "charger_type": "solax_modbus"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"charger_device": device.id}
    )
    assert result["errors"] == {"base": "solax_entities_not_found"}


async def _solax_coordinator(hass):
    device_id = _solax_device(hass)
    entry = MockConfigEntry(
        domain=DOMAIN, version=2,
        data={**HOUSE, **LIMITS, "max_battery_discharge_power": 0.0,
              "charger_type": "solax_modbus", "charger_device": device_id},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return hass.data[DOMAIN][entry.entry_id]


def _house(hass, solar, consumption, soc, battery, use_mode, run_mode="Preparing", current=6):
    hass.states.async_set("sensor.solar", solar)
    hass.states.async_set("sensor.consumption", consumption)
    hass.states.async_set("sensor.grid", 0)
    hass.states.async_set("sensor.battery_soc", soc)
    hass.states.async_set("sensor.battery_power", battery)
    hass.states.async_set("sensor.evc_charge_voltage", 230)
    hass.states.async_set("sensor.evc_charge_power", 0)
    hass.states.async_set("select.garazh_use_mode", use_mode)
    hass.states.async_set("sensor.evc_run_mode", run_mode)
    hass.states.async_set("number.evc_charge_current", current)


async def test_solax_starts_in_fast_from_eco(hass, mock_http):
    coordinator = await _solax_coordinator(hass)
    selects = async_mock_service(hass, "select", "select_option")
    numbers = async_mock_service(hass, "number", "set_value")

    _house(hass, solar=3500, consumption=500, soc=97, battery=0, use_mode="ECO")
    await hass.async_block_till_done()
    selects.clear(); numbers.clear()
    await coordinator.calculate_and_set_current()

    # 3000 W * 0.9 / 230 V = 11.7 -> 11 A
    assert numbers[-1].data["value"] == 11
    assert selects[-1].data == {"entity_id": "select.garazh_use_mode", "option": "Fast"}


async def test_solax_stops_with_stop_mode(hass, mock_http):
    coordinator = await _solax_coordinator(hass)
    selects = async_mock_service(hass, "select", "select_option")
    numbers = async_mock_service(hass, "number", "set_value")

    _house(hass, solar=300, consumption=500, soc=97, battery=0, use_mode="Fast")
    await hass.async_block_till_done()
    selects.clear(); numbers.clear()
    await coordinator.calculate_and_set_current()

    assert selects[-1].data["option"] == "Stop"
    assert not numbers


async def test_solax_ignores_unplugged_car(hass, mock_http):
    coordinator = await _solax_coordinator(hass)
    selects = async_mock_service(hass, "select", "select_option")
    numbers = async_mock_service(hass, "number", "set_value")

    _house(hass, solar=3500, consumption=500, soc=97, battery=0,
           use_mode="Stop", run_mode="Available")
    await hass.async_block_till_done()
    selects.clear(); numbers.clear()
    await coordinator.calculate_and_set_current()

    assert not selects and not numbers
