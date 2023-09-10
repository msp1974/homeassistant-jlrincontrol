"""
Jaguar Landrover Component for In Control API

Includes Sensor Devices and Services

https://github.com/msp1974/homeassistant-jlrincontrol.git
msparker@sky.com
"""
import logging
import uuid
from datetime import datetime, timedelta

import voluptuous as vol
from custom_components.jlrincontrol.config_flow import DEVICE_ID

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID, CONF_PIN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.event import async_call_later

from .const import (
    ATTR_CHARGE_LEVEL,
    ATTR_EXPIRY,
    ATTR_PIN,
    ATTR_TARGET_TEMP,
    ATTR_TARGET_VALUE,
    CONF_ALL_DATA_SENSOR,
    CONF_DEBUG_DATA,
    CONF_DISTANCE_UNIT,
    CONF_HEALTH_UPDATE_INTERVAL,
    DOMAIN,
    HEALTH_UPDATE_TRACKER,
    JLR_DATA,
    JLR_SERVICES,
    PLATFORMS,
    UPDATE_LISTENER,
)
from .coordinator import (
    JLRIncontrolHealthUpdateCoordinator,
    JLRIncontrolUpdateCoordinator,
)

_LOGGER = logging.getLogger(__name__)

MIN_UPDATE_INTERVAL = timedelta(minutes=1)
DEFAULT_UPDATE_INTERVAL = timedelta(minutes=5)

SERVICES_BASE_SCHEMA = {
    vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
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
SERVICES_EXPIRY_SCHEMA = {
    vol.Required(ATTR_EXPIRY): vol.Coerce(datetime),
}


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Migrate old entry."""
    _LOGGER.debug("Migrating from version %s", config_entry.version)

    if config_entry.version == 1:
        new_data = {**config_entry.data}
        new_options = {**config_entry.options}

        # Add fixed device id
        new_data[DEVICE_ID] = str(uuid.uuid4())

        # Move pin to data from options
        new_data[CONF_PIN] = new_options[CONF_PIN]

        # Remove no longer needed options
        remove_options = [
            CONF_PIN,
            CONF_DISTANCE_UNIT,
            CONF_ALL_DATA_SENSOR,
            CONF_DEBUG_DATA,
        ]
        for option in remove_options:
            try:
                del new_options[option]
                _LOGGER.debug("Removed option %s", option)
            except KeyError:
                pass

        config_entry.version = 2
        hass.config_entries.async_update_entry(
            config_entry, data=new_data, options=new_options
        )

    _LOGGER.info("Migration to version %s successful", config_entry.version)

    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Setup JLR InConnect component"""

    def get_schema(schema_list):
        result = {}
        for schema in schema_list:
            result.update(eval(schema))  # pylint: disable=eval-used
        return vol.Schema(cv.make_entity_service_schema(result))

    hass.data.setdefault(DOMAIN, {})

    coordinator = JLRIncontrolUpdateCoordinator(hass, config_entry)

    try:
        await coordinator.async_connect()
    except Exception as ex:
        raise ConfigEntryNotReady from ex

    await coordinator.async_config_entry_first_refresh()

    # Update listener for config option changes
    update_listener = config_entry.add_update_listener(_async_update_listener)

    hass.data[DOMAIN][config_entry.entry_id] = {
        JLR_DATA: coordinator,
        UPDATE_LISTENER: update_listener,
    }

    # Setup health update and repeat interval
    health_update_interval = config_entry.options.get(CONF_HEALTH_UPDATE_INTERVAL, 0)

    if health_update_interval and health_update_interval > 0:
        _LOGGER.info(
            "Vehicle health update on %s minute interval",
            int(health_update_interval),
        )

        health_update_coordinator = JLRIncontrolHealthUpdateCoordinator(
            hass, config_entry, coordinator
        )

        # Add health update listener to config
        hass.data[DOMAIN][config_entry.entry_id][
            HEALTH_UPDATE_TRACKER
        ] = health_update_coordinator

        # Do initial call to health_update service after HASS start up.
        # This speeds up restart.
        # 30 seconds should do it.
        async_call_later(hass, 30, health_update_coordinator.async_update_data)

    else:
        _LOGGER.info(
            "Scheduled vehicle health update is disabled. %s",
            "Set interval in options to enable.",
        )

    # Create vehicle devices
    await async_update_device_registry(hass, config_entry)

    # Setup platforms
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    # Add services
    for service, service_info in JLR_SERVICES.items():
        if service_info.get("custom_service", False):
            _LOGGER.debug("Adding %s service", service)
            hass.services.async_register(
                DOMAIN,
                service,
                coordinator.async_call_service,
                schema=get_schema(service_info.get("schema")),
            )

    return True


async def _async_update_listener(hass: HomeAssistant, config_entry: ConfigEntry):
    """Handle options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_update_device_registry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Update device registry."""
    data = hass.data[DOMAIN][config_entry.entry_id][JLR_DATA]
    device_registry = dr.async_get(hass)
    for vin in data.vehicles:
        device_registry.async_get_or_create(
            config_entry_id=config_entry.entry_id,
            connections={},
            identifiers={(DOMAIN, vin)},
            manufacturer=data.vehicles[vin].attributes.get("vehicleBrand"),
            name=data.vehicles[vin].attributes.get("nickname"),
            model=data.vehicles[vin].attributes.get("vehicleType"),
            sw_version=data.vehicles[vin].status.get("TU_STATUS_SW_VERSION_MAIN"),
        )


async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: ConfigEntry, device_entry
) -> bool:
    """Delete device if no longer on account"""
    _LOGGER.warning(device_entry)
    vin = list(device_entry.identifiers)[0][1]
    _LOGGER.warning(vin)
    coordinator = hass.data[DOMAIN][config_entry.entry_id][JLR_DATA]

    if vin in coordinator.vehicles:
        raise HomeAssistantError(
            f"You cannot delete vehicle {device_entry.name} because it is still active on your InControl account"
        )

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Unload a config entry."""
    _LOGGER.info("Unloading JLR InControl Component")

    # Deregister services
    _LOGGER.info("Unregister JLR InControl Services")
    for service in JLR_SERVICES.items():
        _LOGGER.info("Unregister %s", service[0])
        hass.services.async_remove(DOMAIN, service[0])

    # Remove platform components
    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )

    if unload_ok:
        hass.data[DOMAIN].pop(config_entry.entry_id)

    return unload_ok
