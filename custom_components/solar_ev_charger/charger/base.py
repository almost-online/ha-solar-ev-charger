"""Base class for EV charger drivers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..coordinator import SolarEVChargerCoordinator


class ChargerDriver(ABC):
    """Applies the coordinator's target current to a specific charger."""

    # Custom chargers stop as soon as SOC drops below the minimum.
    # Drivers with their own start/stop policy set this to False.
    stop_below_min_soc = True

    def __init__(self, coordinator: SolarEVChargerCoordinator) -> None:
        """Initialize."""
        self.coordinator = coordinator
        self.hass = coordinator.hass

    @property
    @abstractmethod
    def power_entity(self) -> str | None:
        """Sensor with the charger's current power in watts."""

    @property
    def voltage_entity(self) -> str | None:
        """Sensor with the charger's voltage, if the charger provides one."""
        return None

    @property
    def tracked_entities(self) -> list[str]:
        """Charger entities whose changes trigger a recalculation."""
        return [entity for entity in (self.power_entity, self.voltage_entity) if entity]

    @property
    def extra_attributes(self) -> dict[str, Any]:
        """Driver state for the status sensor."""
        return {}

    @abstractmethod
    async def async_apply(
        self,
        target_amps: float,
        battery_soc: float | None,
        battery_power: float | None,
    ) -> None:
        """Bring the charger to the target current. 0 means stop."""
