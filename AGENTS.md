# Solar EV Charger — agent guide

Home Assistant HACS integration. Domain `solar_ev_charger`. It drives an EV charger (a Custom `number` entity or a Solax ModBus charger) so charging follows solar surplus and a battery-discharge allowance.

Read `custom_components/solar_ev_charger/coordinator.py` before changing control behavior. The last assignment to `raw_available` is the formula that runs. Comments above it describe an older grid equation and are not executed.

User-facing behavior is in `README.md`. If README and the coordinator disagree, trust the coordinator and update README in the same change.

## Surplus and current

Power sensors are watts. The discharge limit is entered in kW and stored in watts (`config_flow` multiplies by 1000).

```text
raw_available = solar_power - consumption_power + max_battery_discharge_power
target_amps = floor((smoothed(raw_available) * ev_share) / (voltage * phases))
```

- `phases` is hardcoded to `1`.
- Default discharge allowance is 1000 W. Default min SOC is 90. Default smoothing is 30 s. Default voltage is 230 V.
- SOC below `min_battery_soc` calls `driver.async_apply(0, ...)` and returns, but only for drivers with `stop_below_min_soc = True` (Custom). Solax skips this and leaves it to its start/stop policy.
- `ignore_battery_charging` or a missing SOC sets `ev_share` to `1.0`.
- At min SOC, `ev_share` is `0.6`. At or above `(100 + min_battery_soc) / 2`, it is `0.9`.
- Below 6 A (`MIN_CHARGE_AMPS`) the target becomes 0, then the deadband and smoothing rules run. Above `max_current` the target is clamped. Other targets use `math.floor`.
- Custom: start from 0 A and stop to 0 A skip the smoothing wait. Other changes wait `smoothing_period` and ignore a difference of 0.5 A or less.

## Charger types

`charger_type` in entry data picks the driver. Config entry `VERSION = 2`. `async_migrate_entry` turns v1 entries into `custom` with the same entities, so old setups behave as before.

- `custom` (default): user power sensor and `number` current entity. Behavior is the pre-1.3 coordinator logic, moved into `charger/custom.py`.
- `solax_modbus`: one device from the `solax_modbus` integration. Its Charge Power and Charge Voltage sensors feed `ev_power` and `voltage`; a voltage entity set in the user step wins. Only acts when Run Mode is not `Available`, `Unavailable`, `Faulted` or `Update`.
  - Start: write Charge Current (at least 6 A), then Charger Use Mode `Fast`. `ECO` and `Green` are switched to `Fast` too.
  - Stop: Charger Use Mode `Stop`. No 6 A write.
  - Start and stop both wait for the wish to hold `smoothing_period`. No immediate 0 ↔ 6 A path.
  - Charging while the battery discharges below -100 W with SOC under `min_battery_soc` for `smoothing_period` stops and sets a latch. The latch blocks starts until SOC is back at the minimum. Below the minimum, a start also needs the battery to be charging.
  - Current changes while in `Fast` keep the 0.5 A deadband and the `smoothing_period` wait.

Grid export is positive and battery charging is positive. Neither sensor is in the active surplus formula. Both are copied onto the status sensor for the Lovelace card.

### Check these before editing the coordinator

- The interpolation branch is `max(linear_share, 1)`. A share between 0.6 and 0.9 therefore becomes `1.0`. The 60% and 90% branches still apply at the endpoints.
- Custom only: `CustomChargerDriver._set_charger_current` (`charger/custom.py`) rewrites `new_setpoint <= 0` to 6 A before `number.set_value`. A requested stop currently sends 6 A, and the `new_setpoint == 0` log path in the exception handler does not run. Solax stops with Charger Use Mode `Stop` instead.
- Number entities update coordinator fields in memory only. They are not saved on the config entry. Reload restores setup values.
- `CONF_EV_CHARGER_MAX_CURRENT_ENTITY` in `const.py` is unused.

Do not "correct" either behavior unless the task is to change it. Update README when you do.

## Where code lives

| Path | Role |
| --- | --- |
| `coordinator.py` | Surplus, SOC share, power smoothing, target amps, `device_info`. Hands the target to `self.driver` |
| `charger/__init__.py` | `CHARGER_DRIVERS` registry by `charger_type`. Register new charger types here |
| `charger/base.py` | `ChargerDriver`: `power_entity`, `voltage_entity`, `tracked_entities`, `async_apply` |
| `charger/custom.py` | Custom: user `number` for amps, the 6 A stop rewrite, smoothing and deadband |
| `charger/solax.py` | Solax ModBus: entities found by `unique_id` `{prefix}_{key}` on the device, Fast/Stop, Charge Current |
| `charger/solax_policy.py` | Pure start/stop debounce and battery latch for Solax. Tested in `tests/` |
| `config_flow.py` | Setup and reconfigure. kW in the form, watts in entry data |
| `const.py` | Keys and defaults |
| `sensor.py` | Status (`Disabled`, `Manual`, `Priority EV`, `Solar Only`) plus mirrored power sensors |
| `switch.py` | Enabled, Solar Only, Ignore Battery Charging |
| `number.py` | Max current (A), min SOC (%), max discharge (kW), smoothing (s) |
| `__init__.py` | Setup, static path `/{DOMAIN}/www`, Lovelace resource registration |
| `www/solar-ev-charger-card.js` | Card and `SolarEVChargerDashboardStrategy` |
| `dashboard.yaml` | Dashboard blueprint |
| `manifest.json` | Version. Bump it on every integration code change |
| `strings.json`, `translations/en.json` | Config-flow copy. Keep them in sync |

Keep control math in `SolarEVChargerCoordinator`. Keep using `async_track_state_change_event` for entity updates.

## Versioning

Bump `manifest.json` `version` when Python, the card, or translations change:

- Patch `1.2.x` — compatible bug fix
- Minor `1.x.0` — compatible feature
- Major `x.0.0` — breaking config or entity changes

Documentation-only edits do not need a bump. Current version is in `manifest.json`.

## Live Home Assistant

The only MCP server is `home-assistant` in `~/.cursor/mcp.json`. Point it at the Home Assistant admin MCP API (`/api/mcp/homeassistant`) with the URL and token from the environment, not hardcoded in this repo. Do not copy tokens into the repo or into chat. ESPHome is not part of this integration and has no MCP server here.

Tools: `search__search`, `homeassistant__render_template`, `history__get_history`, `config__get_config_entries`, `system_log__get_entries`, `hassio__get_logs`, `homeassistant__search_actions`, `homeassistant__call_action`.

Delegate entity and log lookups to the `ha-live` subagent. Delegate a review of coordinator math to `charger-logic`.

Do not call `homeassistant__call_action` or `number.set_value` unless the user asked to change the live system. Do not reload the config entry without a request. Do not paste secrets into files or replies.

Confirm sensor units and signs on the live entities before changing the surplus formula. Solar, consumption, grid, battery, and EV power are watts. SOC is percent. Charger control is amps.
