# AI Agent Instruction: Solar EV Charger Integration

Maintain the Solar EV Charger Home Assistant integration (`solar_ev_charger`). Cursor agents also follow `AGENTS.md` at the repo root. If this file and `AGENTS.md` disagree, follow `AGENTS.md` and the code.

## Purpose

Set the EV charger current (`number` entity) from solar surplus and a battery-discharge allowance.

## Logic (`coordinator.py`)

The running surplus formula is the last assignment:

`raw_available = solar_power - consumption_power + max_battery_discharge_power`

Comments above that line describe an older `(-grid) + ev + battery` equation. That equation is not executed. Grid export is positive. Battery charging is positive. Both are for the energy-flow card only.

- Smooth `raw_available` over `smoothing_period`.
- SOC < `min_battery_soc`: call `_set_charger_current(0)` and return.
- `ignore_battery_charging`, or no SOC: `ev_share = 1.0`.
- SOC at the minimum: `ev_share = 0.6`. At or above `(100 + min_battery_soc) / 2`: `ev_share = 0.9`.
- The branch between those points uses `max(linear_share, 1)`, so the share becomes `1.0` there.
- `target_amps = floor(smoothed * ev_share / (voltage * phases))` with `phases = 1`.
- Below 6 A the target is 0. Above max current it is clamped.
- `_set_charger_current` currently rewrites a setpoint `<= 0` to 6 A before `number.set_value`. A stop therefore sends 6 A. Do not treat that as the design unless the task is to change it.
- Wait `smoothing_period` between changes. A 0.5 A deadband applies. Start from 0 A and stop to 0 A skip the wait.

## Config and entities

See `const.py` and `config_flow.py`. Discharge power is kW in the form and watts in the entry. Number entities (`number.py`) change coordinator memory only. Switches: Enabled, Solar Only, Ignore Battery Charging. Status sensor: Disabled, Manual, Priority EV, Solar Only.

## Files

`__init__.py` setup and Lovelace resource. `sensor.py`, `switch.py`, `number.py` platforms. Card: `custom_components/solar_ev_charger/www/solar-ev-charger-card.js`. Blueprint: `dashboard.yaml`.

Keep math in `SolarEVChargerCoordinator`. Keep `async_track_state_change_event`.

## Versioning

Bump `manifest.json` after any integration code change. Patch for fixes, minor for compatible features, major for breaking changes.

## Live systems

Use MCP `home-assistant` (`/api/mcp/homeassistant`) from `~/.cursor/mcp.json`. Do not commit tokens. Do not call charger write actions unless the user asked. ESPHome is not used by this integration.
