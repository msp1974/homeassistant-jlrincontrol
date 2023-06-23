"""
Jaguar Landrover Component for In Control API

Includes Sensor Devices and Services

https://github.com/msp1974/homeassistant-jlrincontrol.git
msparker@sky.com
"""
import asyncio
import logging
from datetime import timedelta

import voluptuous as vol
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.event import (
    async_call_later,
    async_track_time_interval,
)

from .const import (
    ATTR_CHARGE_LEVEL,
    ATTR_PIN,
    ATTR_TARGET_TEMP,
    ATTR_TARGET_VALUE,
    CONF_HEALTH_UPDATE_INTERVAL,
    DOMAIN,
    HEALTH_UPDATE_TRACKER,
    JLR_DATA,
    JLR_SERVICES,
    PLATFORMS,
    UPDATE_LISTENER,
)
from .coordinator import JLRIncontrolUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

MIN_UPDATE_INTERVAL = timedelta(minutes=1)
DEFAULT_UPDATE_INTERVAL = timedelta(minutes=5)

SERVICES_BASE_SCHEMA = {
    vol.Required(ATTR_ENTITY_ID): cv.entity_id,
}
SERVICES_PIN_SCHEMA = {
    vol.Required(ATTR_PIN): vol.Coerce(str),
}
SERVICES_TARGET_TEMP_SCHEMA = {
    vol.Required(ATTR_TARGET_TEMP): vol.Coerce(int),
}
SERVICES_TARGET_VALUE_SCHEMA = {
    vol.Required(ATTR_TARGET_VALUE): vol.Coerce(int),
}
SERVICES_CHARGE_LEVEL_SCHEMA = {
    vol.Required(ATTR_CHARGE_LEVEL): vol.Coerce(int),
}


async def async_setup_entry(hass, config_entry):
    """Setup JLR InConnect component"""

    def get_schema(schema_list):
        result = {}
        for schema in schema_list:
            result.update(eval(schema))
        return vol.Schema(result)

    health_update_track = None
    hass.data.setdefault(DOMAIN, {})

    coordinator = JLRIncontrolUpdateCoordinator(hass, config_entry)

    try:
        await coordinator.async_connect()
    except Exception as ex:
        raise ConfigEntryNotReady from ex

    await coordinator.async_config_entry_first_refresh()

    health_update_interval = config_entry.options.get(
        CONF_HEALTH_UPDATE_INTERVAL, 0
    )

    # Schedule health update and repeat interval
    if health_update_interval and health_update_interval > 0:
        _LOGGER.info(
            "Vehicle health update on %s minute interval.",
            int(health_update_interval),
        )
        # Do initial call to health_update service after HASS start up.
        # This speeds up restart.
        # 30 seconds should do it.
        async_call_later(hass, 30, coordinator.async_health_update)

        health_update_track = async_track_time_interval(
            hass,
            coordinator.async_health_update,
            timedelta(minutes=health_update_interval),
        )
    else:
        _LOGGER.info(
            "Scheduled vehicle health update is disabled. %s",
            "Set interval in options to enable.",
        )

    # Update listener for config option changes
    update_listener = config_entry.add_update_listener(_async_update_listener)

    hass.data[DOMAIN][config_entry.entry_id] = {
        JLR_DATA: coordinator,
        HEALTH_UPDATE_TRACKER: health_update_track,
        UPDATE_LISTENER: update_listener,
    }

    # for vehicle in data.vehicles:
    for platform in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(
                config_entry, platform
            )
        )

    # Add services
    for service, service_info in JLR_SERVICES.items():
        _LOGGER.debug("Adding %s service", service)
        hass.services.async_register(
            DOMAIN,
            service,
            coordinator.async_call_service,
            schema=get_schema(service_info.get("schema")),
        )

    # Create vehicle devices
    await async_update_device_registry(hass, config_entry)

    return True


async def _async_update_listener(hass, config_entry):
    """Handle options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_update_device_registry(hass, config_entry):
    """Update device registry."""
    data = hass.data[DOMAIN][config_entry.entry_id][JLR_DATA]
    device_registry = dr.async_get(hass)
    for vin in data.vehicles:
        _LOGGER.error("VEHILCE: %s", vin)
        device_registry.async_get_or_create(
            config_entry_id=config_entry.entry_id,
            connections={},
            identifiers={(DOMAIN, vin)},
            manufacturer=data.vehicles[vin].attributes.get("vehicleBrand"),
            name=data.vehicles[vin].attributes.get("nickname"),
            model=data.vehicles[vin].attributes.get("vehicleType"),
            sw_version=data.vehicles[vin].status.get(
                "TU_STATUS_SW_VERSION_MAIN"
            ),
        )


async def async_unload_entry(hass, config_entry):
    """Unload a config entry."""
    _LOGGER.info("Unloading JLR InControl Component")

    # Deregister services
    _LOGGER.info("Unregister JLR InControl Services")
    for service in JLR_SERVICES.items():
        _LOGGER.info("Unregister %s", service[0])
        hass.services.async_remove(DOMAIN, service[0])

    # Stop scheduled updates
    hass.data[DOMAIN][config_entry.entry_id][UPDATE_LISTENER]()
    if hass.data[DOMAIN][config_entry.entry_id][HEALTH_UPDATE_TRACKER]:
        hass.data[DOMAIN][config_entry.entry_id][HEALTH_UPDATE_TRACKER]()

    # Remove platform components
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(
                    config_entry, platform
                )
                for platform in PLATFORMS
            ]
        )
    )

    if unload_ok:
        hass.data[DOMAIN].pop(config_entry.entry_id)

    return unload_ok
