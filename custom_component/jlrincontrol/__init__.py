"""
Jaguar Landrover Component for In Control API

Includes Sensor Devices and Services

https://github.com/msp1974/homeassistant-jlrincontrol.git
msparker@sky.com
"""

import jlrpy
import json

import logging
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.dispatcher import (
    async_dispatcher_send,
    async_dispatcher_connect,
)
from homeassistant.helpers.entity import Entity

from datetime import timedelta
from homeassistant.const import (
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_RESOURCES,
    CONF_NAME,
    CONF_SCAN_INTERVAL,
)
from homeassistant.helpers.discovery import async_load_platform
from .const import METERS_TO_MILES

# from homeassistant.helpers.entity import Entity
# from homeassistant.helpers.dispatcher import dispatcher_send
# from homeassistant.helpers.icon import icon_for_battery_level

_LOGGER = logging.getLogger(__name__)

DOMAIN = "jlrincontrol"
DATA_KEY = DOMAIN

MIN_UPDATE_INTERVAL = timedelta(minutes=1)
DEFAULT_UPDATE_INTERVAL = timedelta(minutes=5)

PLATFORMS = ["sensor", "lock"]

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


async def async_setup(hass, config):
    """Setup JLR InConnect component"""
    # interval = config[DOMAIN].get(CONF_SCAN_INTERVAL)

    data = JLRApiHandler(config)
    await data.async_update()

    if not data.vehicles:
        # No vehicles or wrong credentials
        _LOGGER.error("Unable to get vehicles from api.  Check credentials")
        return False

    _LOGGER.debug("Connected to API")
    hass.data[DATA_KEY] = data

    for platform in PLATFORMS:
        hass.async_create_task(async_load_platform(hass, platform, DOMAIN, {}, config))

    return True


class JLRApiHandler:
    def __init__(self, config):
        self.config = config
        self.vehicles = None
        self.connection = None
        self.attributes = None
        self.status = None
        self.position = None
        self.user_info = None
        self.user_preferences = None

        _LOGGER.debug("Creating connection to JLR InControl API")
        self.connection = jlrpy.Connection(
            email=self.config[DOMAIN].get(CONF_USERNAME),
            password=self.config[DOMAIN].get(CONF_PASSWORD),
        )

        self.vehicles = self.connection.vehicles
        self.user_info = self.connection.get_user_info()

        _LOGGER.debug("User Info - {}".format(self.user_preferences))

        u = self.user_info["contact"].get("userPreferences")
        if u:
            self.user_preferences = u.get("unitsOfMeasurement")
        else:
            # Set to default if cannot read from api
            # Need to sort out a retry if it fails
            self.user_preferences = (
                "Miles UkGallons Celsius DistPerVol kWhPer100Dist kWh"
            )

    async def async_update(self):
        self.attributes = self.vehicles[0].get_attributes()
        self.position = self.vehicles[0].get_position()
        status = self.vehicles[0].get_status()
        self.status = {d["key"]: d["value"] for d in status["vehicleStatus"]}

        _LOGGER.debug("API REG - {}".format(self.attributes.get("registrationNumber")))

        return True

    def get_odometer(self):
        if "Miles" in self.user_preferences:
            return int(self.status.get("ODOMETER_MILES"))
        else:
            return int(int(self.status.get("ODOMETER_METERS")) / 1000)


class JLREntity(Entity):
    def __init__(self, data, sensor_type):
        """Create a new generic Dyson sensor."""
        self._name = None
        self._sensor_type = sensor_type
        self._icon = "mid:cloud"

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def name(self):
        return self._name

    @property
    def icon(self):
        """Return the icon for this sensor."""
        return self._icon

    @property
    def unique_id(self):
        """Return the sensor's unique id."""
        return f"JagXF-{self._sensor_type}--{self._name}"

    async def async_update(self):
        _LOGGER.debug("Update requested")
        await self.data.async_update()
        return True

    async def async_added_to_hass(self):
        """Subscribe for update from the hub"""

        async def async_update_state():
            """Update sensor state."""
            await self.async_update_ha_state(True)

        async_dispatcher_connect(self.hass, "WiserHubUpdateMessage", async_update_state)
