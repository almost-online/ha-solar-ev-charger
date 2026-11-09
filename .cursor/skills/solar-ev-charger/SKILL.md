---
name: solar-ev-charger
description: >-
  Maintain the Solar EV Charger Home Assistant integration (domain
  solar_ev_charger). Use when editing surplus math, battery SOC share,
  smoothing, the config flow, sensors, switches, number entities, the
  Lovelace card, or manifest version for this repo.
---

# Solar EV Charger

## Before editing

1. Read `AGENTS.md` and `coordinator.py`. The executed surplus line is:

```python
raw_available = solar_power - consumption_power + self.max_battery_discharge_power
```

2. Do not restore the commented `(-grid_power) + ev_power + battery_power` equation.
3. Note two current behaviors before "fixing" them: interpolation uses `max(linear_share, 1)` so the middle SOC band is 100%, and the Custom driver's `_set_charger_current` sends 6 A when the setpoint is `<= 0`. Solax stops with Charger Use Mode `Stop`.

## Change checklist

- Math stays in `SolarEVChargerCoordinator`.
- New config keys: `const.py`, `config_flow.py` (including reconfigure), `strings.json`, `translations/en.json`.
- Discharge power: kW in the form and number entity, watts on the coordinator (`* 1000`).
- Card data comes from status-sensor attributes: `solar`, `grid`, `consumption`, `battery_power`, `battery_soc`, `ev_power`.
- Bump `manifest.json` for code changes. Update `README.md` when user-visible behavior changes.

## Signs and units

Watts for power. Percent for SOC. Amps for charger current. Volts for voltage. Export positive. Battery charging positive.
