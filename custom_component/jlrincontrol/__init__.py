"""
Jaguar Landrover Component for In Control API

Includes Sensor Devices and Services

https://github.com/msp974/jlr_home_assistant
msparker@sky.com
"""

import jlrpy
import json

import logging
import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from datetime import timedelta
from homeassistant.const import (
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_RESOURCES,
    CONF_NAME,
    CONF_SCAN_INTERVAL,
)
from homeassistant.helpers.discovery import load_platform

# from homeassistant.helpers.entity import Entity
# from homeassistant.helpers.dispatcher import dispatcher_send
# from homeassistant.helpers.icon import icon_for_battery_level

_LOGGER = logging.getLogger(__name__)

DOMAIN = "jlrincontrol"
DATA_KEY = DOMAIN

MIN_UPDATE_INTERVAL = timedelta(minutes=1)
DEFAULT_UPDATE_INTERVAL = timedelta(minutes=5)

PLATFORMS = {"sensor": "sensor"}
"""
,
    "binary_sensor": "binary_sensor",
    "lock": "lock",
    "device_tracker": "device_tracker",
    "switch": "switch",
    "climate": "climate",
}
"""
RESOURCES = [
    "position",
    "distance",
    "climatisation",
    "window_heater",
    "combustion_engine_heating",
    "charging",
    "battery_level",
    "fuel_level",
    "service_inspection",
    "oil_inspection",
    "last_connected",
    "charging_time_left",
    "electric_range",
    "combustion_range",
    "combined_range",
    "charge_max_ampere",
    "climatisation_target_temperature",
    "external_power",
    "parking_light",
    "climatisation_without_external_power",
    "door_locked",
    "trunk_locked",
    "request_in_progress",
]

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): (
                    vol.All(cv.time_period, vol.Clamp(min=MIN_UPDATE_INTERVAL))
                ),
                vol.Optional(CONF_NAME, default={}): vol.Schema({cv.slug: cv.string}),
                vol.Optional(CONF_RESOURCES): vol.All(
                    cv.ensure_list, [vol.In(RESOURCES)]
                ),
            }
        ),
    },
    extra=vol.ALLOW_EXTRA,
)


def setup(hass, config):
    """Setup JLR InConnect component"""
    # interval = config[DOMAIN].get(CONF_SCAN_INTERVAL)

    data = JLRApiHandler(config)

    if not data.vehicles:
        # No vehicles or wrong credentials
        _LOGGER.error("Unable to get vehicles from api.  Check credentials")
        return False

    _LOGGER.debug("Connected to API")
    hass.data[DATA_KEY] = data

    for platform in PLATFORMS:
        load_platform(hass, platform, DOMAIN, {}, config)

    return True


class JLRApiHandler:
    def __init__(self, config):
        self.config = config
        self.vehicles = None
        self.connection = None
        self.attributes = None

        _LOGGER.debug("Creating connection to JLR InControl API")
        self.connection = jlrpy.Connection(
            email=self.config[DOMAIN].get(CONF_USERNAME),
            password=self.config[DOMAIN].get(CONF_PASSWORD),
        )

        self.vehicles = self.connection.vehicles
        self.attributes = self.vehicles[0].get_attributes()
        _LOGGER.debug("API REG - {}".format(self.attributes.get("registrationNumber")))

    def update(self):
        self.attributes = self.vehicles[0].get_attributes()
        return True
