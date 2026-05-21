"""The Solar EV Charger integration."""
from __future__ import annotations

import logging

import os
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace import resources

from .const import DOMAIN
from .coordinator import SolarEVChargerCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Solar EV Charger from a config entry."""
    coordinator = SolarEVChargerCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Register static path for custom card
    await hass.http.async_register_static_paths([
        StaticPathConfig(
            f"/{DOMAIN}/www",
            hass.config.path(f"custom_components/{DOMAIN}/www"),
            False
        )
    ])
    _LOGGER.debug("Registered static path for custom card at /%s/www", DOMAIN)

    # Programmatically register the frontend resource
    url = f"/{DOMAIN}/www/solar-ev-charger-card.js"
    
    # Resources are managed in hass.data["lovelace"]["resources"]
    lovelace_data = hass.data.get("lovelace")
    if lovelace_data and "resources" in lovelace_data:
        resource_manager = lovelace_data["resources"]
        # Ensure resources are loaded
        if not resource_manager.loaded:
            await resource_manager.async_load()
            
        if not any(resource["url"] == url for resource in resource_manager.async_items()):
            await resource_manager.async_create_item({"res_type": "module", "url": url})
            _LOGGER.debug("Registered frontend resource: %s", url)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
