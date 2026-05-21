# AI Agent Instruction: Solar EV Charger Integration

You are an AI agent tasked with maintaining, improving, or troubleshooting the "Solar EV Charger" Home Assistant integration. This integration is designed to optimize EV charging by using surplus solar power.

## Project Context
- **Name**: Solar EV Charger
- **Domain**: `solar_ev_charger`
- **Type**: Home Assistant HACS Integration
- **Purpose**: Controls an EV charger's current (via a `number` entity) based on grid export and battery power to ensure only solar energy is used for charging.

## Key Logic (coordinator.py)
- **Surplus Calculation**: 
  - `surplus = grid_power + max(0, battery_power)`
  - `grid_power`: Positive value indicates export to grid (surplus).
  - `battery_power`: Positive value indicates battery is charging (surplus).
- **Current Adjustment**:
  - `change_amps = surplus_power / (voltage * phases)`
  - `voltage` is currently hardcoded to 230V.
  - `phases` is currently hardcoded to 1.
  - The integration adjusts the `ev_charger_control_current_entity` (a Home Assistant `number` entity).

## Configured Entities (via Config Flow)
- `solar_power_entity`: Total solar production.
- `consumption_power_entity`: Total house consumption.
- `grid_power_entity`: Grid export (positive) / import (negative).
- `battery_power_entity`: Battery charge (positive) / discharge (negative).
- `battery_soc_entity`: Battery state of charge.
- `ev_charger_power_entity`: Current power used by the EV charger.
- `ev_charger_control_current_entity`: The `number` entity used to set the charging current.
- `ev_charger_max_current`: User-defined limit for the charging current.

## Codebase Structure
- `__init__.py`: Integration setup and platform forwarding.
- `config_flow.py`: UI configuration handler.
- `const.py`: Shared constants.
- `coordinator.py`: The "brain" - contains the logic for surplus calculation and charger control.
- `sensor.py`: Provides a status sensor (Disabled, Manual, Solar Only).
- `switch.py`: Provides switches to Enable/Disable the integration and toggle Solar Only mode.
- `manifest.json`: Integration metadata.

## Instructions for AI Tasks
1. **Adding Features**:
   - If adding support for 3-phase charging, update the `calculate_and_set_current` logic in `coordinator.py` and potentially add a config option in `config_flow.py`.
   - If adding a minimum SOC requirement for the battery, update `coordinator.py`.
2. **Bug Fixing**:
   - Check the unit of measurement for power entities (assumed Watts).
   - Ensure `voltage` and `phases` assumptions match the user's hardware.
3. **Refactoring**:
   - Keep the logic centralized in the `SolarEVChargerCoordinator`.
   - Maintain the use of `async_track_state_change_event` for reactive updates.
