# Solar EV Charger HACS Integration

This Home Assistant integration allows you to automatically control your EV charger based on available solar energy. It monitors your solar production, house consumption, grid export/import, and battery state to adjust the EV charging current.

## Features

- **Solar Only Mode**: Adjusts EV charging current to match available solar surplus.
- **Energy Flow Diagram**: Visualizes power distribution between solar, grid, battery, and EV.
- **Grid-Aware**: Uses grid export/import data to determine available power.
- **Battery-Aware**: Considers power going into your home battery as available surplus for the EV.
- **Dynamic Control**: Reacts to changes in household consumption and solar production in real-time.

## UI Component (Energy Flow Diagram)

This integration includes a custom Lovelace card to visualize the energy flow.

### Manual Setup
To use the card, you can use the built-in Dashboard Blueprint or add it manually.

#### Dashboard Blueprint
If your Home Assistant version supports Dashboard Blueprints, you can import the pre-made "Solar EV Charger Dashboard" which automatically configures the card for you.

#### Manual Card Setup
1. Click "Add Card" -> "Manual".
2. Use the following YAML:
```yaml
type: custom:solar-ev-charger-card
entity: sensor.solar_ev_charger_status
```

*Note: Ensure you replace `sensor.solar_ev_charger_status` with your actual integration sensor if it differs.*

## Configuration

During setup, you will be asked to provide the following entities:

- **Solar Power**: Current power produced by solar panels (Watts).
- **Consumption Power**: Total household consumption (Watts).
- **Grid Power**: Power being exported to or imported from the grid. **Export must be positive, Import must be negative.**
- **Battery Power (Optional)**: Power going into or out of the home battery. **Discharging must be positive, Charging must be negative.**
- **Battery SOC (Optional)**: State of charge of the home battery (%).
- **EV Charger Power**: Current power consumption of the EV charger (Watts).
- **EV Charger Control Current**: A `number` entity that controls the charger's current (Amps).
- **Max Current**: The maximum current allowed for the EV charger.

## How it works

The integration calculates the available power using the following logic:
`Available Power = (-Grid Power) + EV Power - Battery Power`

Where:
- **Grid Power**: Positive for Export, Negative for Import.
- **Battery Power**: Positive for Discharging, Negative for Charging.

It then calculates an EV share based on Battery SOC:
- If SOC < `min_battery_soc`, EV charging stops.
- If SOC > `min_battery_soc`, power is shared between Battery and EV (scaling from 60% to 90% for EV).

The charging current is adjusted according to:
`Target Amps = (Available Power * EV Share) / Voltage`

The setpoint is updated with a smoothing period and a 0.5A deadband to protect your charger.

## Installation

1. Install via HACS (Custom Repository).
2. Restart Home Assistant.
3. Add the "Solar EV Charger" integration from the Devices & Services menu.
