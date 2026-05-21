# Solar EV Charger HACS Integration

This Home Assistant integration allows you to automatically control your EV charger based on available solar energy. It monitors your solar production, house consumption, grid export/import, and battery state to adjust the EV charging current.

## Features

- **Solar Only Mode**: Adjusts EV charging current to match available solar surplus.
- **Grid-Aware**: Uses grid export/import data to determine available power.
- **Battery-Aware**: Considers power going into your home battery as available surplus for the EV.
- **Dynamic Control**: Reacts to changes in household consumption and solar production in real-time.

## Configuration

During setup, you will be asked to provide the following entities:

- **Solar Power**: Current power produced by solar panels (Watts).
- **Consumption Power**: Total household consumption (Watts).
- **Grid Power**: Power being exported to or imported from the grid. **Export must be positive, Import must be negative.**
- **Battery Power (Optional)**: Power going into or out of the home battery. **Charging must be positive, Discharging must be negative.**
- **Battery SOC (Optional)**: State of charge of the home battery (%).
- **EV Charger Power**: Current power consumption of the EV charger (Watts).
- **EV Charger Control Current**: A `number` entity that controls the charger's current (Amps).
- **Max Current**: The maximum current allowed for the EV charger.

## How it works

The integration calculates the "surplus" power as:
`Surplus = Grid Power + max(0, Battery Power)`

It then adjusts the EV charger's current setpoint based on this surplus, assuming a 230V single-phase connection (default logic).

`New Current = Current Current + (Surplus / 230V)`

The setpoint is updated if the change is greater than 0.5A.

## Installation

1. Install via HACS (Custom Repository).
2. Restart Home Assistant.
3. Add the "Solar EV Charger" integration from the Devices & Services menu.
