"""Start/stop decision for chargers that switch modes instead of writing 0 A.

Kept free of Home Assistant imports so it can be unit tested directly.
"""
from __future__ import annotations

from dataclasses import dataclass

# Battery power below this (W, charging positive) counts as discharging.
# Absorbs inverter noise around 0 W.
DISCHARGE_THRESHOLD = -100.0


@dataclass
class SolaxStartStopPolicy:
    """Debounced start/stop with a latch after battery-backed stops.

    - Start and stop both need the wish to hold for `smoothing_period`.
    - While charging, if the battery discharges with SOC below the minimum for
      `smoothing_period`, charging stops and the latch is set.
    - The latch blocks starts until SOC reaches the minimum again, so a load
      switching off cannot restart the charger into the same deficit.
    - Below the minimum SOC a start also needs the battery to be charging.
    """

    smoothing_period: float
    latched: bool = False
    _pending: bool | None = None
    _pending_since: float = 0.0
    _discharge_since: float | None = None

    def reset_pending(self) -> None:
        """Forget timers, e.g. while no car is connected."""
        self._pending = None
        self._discharge_since = None

    def decide(
        self,
        now: float,
        active: bool,
        target_amps: float,
        battery_soc: float | None,
        battery_power: float | None,
        min_battery_soc: float,
    ) -> bool:
        """Return whether the charger should be charging."""
        below_min = battery_soc is not None and battery_soc < min_battery_soc

        if self.latched and not below_min:
            self.latched = False

        if active and below_min and battery_power is not None and battery_power < DISCHARGE_THRESHOLD:
            if self._discharge_since is None:
                self._discharge_since = now
            if now - self._discharge_since >= self.smoothing_period:
                self.latched = True
                self.reset_pending()
                return False
        else:
            self._discharge_since = None

        if self.latched:
            self._pending = None
            return False

        want = target_amps > 0
        if want and not active and below_min and (battery_power is None or battery_power <= 0):
            want = False

        if want == active:
            self._pending = None
            return active

        if self._pending != want:
            self._pending = want
            self._pending_since = now

        if now - self._pending_since >= self.smoothing_period:
            self._pending = None
            return want
        return active
