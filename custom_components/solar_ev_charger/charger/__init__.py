"""EV charger drivers. Add a new charger type by registering its driver here."""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..const import CHARGER_TYPE_CUSTOM, CHARGER_TYPE_SOLAX_MODBUS, CONF_CHARGER_TYPE
from .base import ChargerDriver
from .custom import CustomChargerDriver
from .solax import SolaxChargerDriver

if TYPE_CHECKING:
    from ..coordinator import SolarEVChargerCoordinator

CHARGER_DRIVERS: dict[str, type[ChargerDriver]] = {
    CHARGER_TYPE_SOLAX_MODBUS: SolaxChargerDriver,
    CHARGER_TYPE_CUSTOM: CustomChargerDriver,
}


def create_driver(coordinator: SolarEVChargerCoordinator) -> ChargerDriver:
    """Build the driver for the config entry's charger type."""
    charger_type = coordinator.entry.data.get(CONF_CHARGER_TYPE, CHARGER_TYPE_CUSTOM)
    return CHARGER_DRIVERS.get(charger_type, CustomChargerDriver)(coordinator)
