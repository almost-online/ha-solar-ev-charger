# AI Agent Instruction: Solar EV Charger Integration

You are an AI agent tasked with maintaining, improving, or troubleshooting the "Solar EV Charger" Home Assistant integration. This integration is designed to optimize EV charging by using surplus solar power.

## Project Context
- **Name**: Solar EV Charger
- **Domain**: `solar_ev_charger`
- **Type**: Home Assistant HACS Integration
- **Purpose**: Controls an EV charger's current (via a `number` entity) based on grid export and battery power to ensure only solar energy is used for charging.

## Key Logic (coordinator.py)
- **Surplus Calculation**: 
  - `total_excess_power = (-grid_power) + ev_power` (smoothed over `smoothing_period`).
  - This represents 100% of raw physical excess power currently available.
- **Battery SOC Logic**:
  - If SOC < `min_battery_soc`, EV charging is stopped (0A).
  - If SOC >= `min_battery_soc`, surplus power is split between battery and EV.
  - EV share scales linearly:
    - 60% at `min_battery_soc`
    - 90% at 95% SOC and above.
- **Smoothing/Damping**:
  - `smoothing_period`: A rolling average of raw excess power is calculated over this duration.
  - Current adjustments (except for immediate start/stop) are delayed by this period.
  - A 0.5A deadband is applied to avoid small fluctuations.
  - Immediate stop (to 0A) or start (from 0A) bypasses the smoothing period.
- **Current Adjustment**:
  - `target_amps = (total_excess_power * ev_share) / (voltage * phases)`
  - Uses `math.floor` for conservative current setting.
  - Minimum charging threshold is 6.0A (IEC 61851). Below this, charging stops (0A).
  - The integration adjusts the `ev_charger_control_current_entity`.

## Configured Entities (via Config Flow)
- `solar_power_entity`: Total solar production.
- `consumption_power_entity`: Total house consumption.
- `grid_power_entity`: Grid export (positive) / import (negative).
- `battery_power_entity`: Battery charge (positive) / discharge (negative).
- `battery_soc_entity`: Battery state of charge.
- `ev_charger_power_entity`: Current power used by the EV charger.
- `ev_charger_control_current_entity`: The `number` entity used to set the charging current.
- `ev_charger_max_current`: User-defined limit for the charging current.
- `ev_charger_voltage_entity`: (Optional) Entity providing real-time voltage.
- `ev_charger_voltage`: (Optional) Fixed voltage value (default 230).
- `min_battery_soc`: (Optional) Minimal SOC to start EV charging (default 90).
- `battery_soc_guardrail`: (Optional) SOC threshold to prioritize house battery (default 50).
- `smoothing_period`: (Optional) Seconds to wait between current adjustments (default 30).

## Codebase Structure
- `__init__.py`: Integration setup and platform forwarding.
- `config_flow.py`: UI configuration handler.
- `const.py`: Shared constants.
- `coordinator.py`: The "brain" - contains the logic for surplus calculation and charger control. Also manages `device_info`.
- `sensor.py`: Provides a status sensor (Disabled, Manual, Solar Only). Associated with the integration device.
- `switch.py`: Provides switches to Enable/Disable the integration and toggle Solar Only mode. Associated with the integration device.
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
