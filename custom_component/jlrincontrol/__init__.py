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
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.dispatcher import (
    async_dispatcher_send,
    async_dispatcher_connect,
)
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle
from datetime import timedelta
from homeassistant.const import (
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_RESOURCES,
    CONF_NAME,
    CONF_SCAN_INTERVAL,
    LENGTH_KILOMETERS,
    LENGTH_MILES,
    PRESSURE_PSI,
    TEMP_CELSIUS,
    TEMP_FAHRENHEIT,
)

from homeassistant.helpers.discovery import async_load_platform
from .const import KMS_TO_MILES, SIGNAL_STATE_UPDATED

# from homeassistant.helpers.entity import Entity
# from homeassistant.helpers.dispatcher import dispatcher_send
# from homeassistant.helpers.icon import icon_for_battery_level

_LOGGER = logging.getLogger(__name__)

DOMAIN = "jlrincontrol"
DATA_KEY = DOMAIN

CONF_PIN = "pin"

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
                vol.Optional(CONF_PIN): cv.string,
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

    data = JLRApiHandler(hass, config)
    await data.async_update()

    if not data.vehicle:
        # No vehicles or wrong credentials
        _LOGGER.error("Unable to get vehicles from api.  Check credentials")
        return False

    _LOGGER.debug("Connected to API")
    hass.data[DATA_KEY] = data

    for platform in PLATFORMS:
        hass.async_create_task(async_load_platform(hass, platform, DOMAIN, {}, config))

    return True


class JLRApiHandler:
    def __init__(self, hass, config):
        self._hass = hass
        self.config = config
        self.vehicle = None
        self.connection = None
        self.attributes = None
        self.status = None
        self.wakeup = None
        self.position = None
        self.user_info = None
        self.user_preferences = None

        _LOGGER.debug("Creating connection to JLR InControl API")
        self.connection = jlrpy.Connection(
            email=self.config[DOMAIN].get(CONF_USERNAME),
            password=self.config[DOMAIN].get(CONF_PASSWORD),
        )

        # Get one time info
        self.vehicle = self.connection.vehicles[0]
        self.user_info = self.connection.get_user_info()
        self.attributes = self.vehicle.get_attributes()

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

    @callback
    def schedule_next_update(self):
        self._hass.async_create_task(self.async_update())

    @callback
    def schedule_next_health_update(self):
        self._hass.async_create_task(self.async_update())

    @Throttle(timedelta(seconds=30))
    async def async_update(self):
        self.position = self.vehicle.get_position()
        status = self.vehicle.get_status()
        self.status = {d["key"]: d["value"] for d in status["vehicleStatus"]}
        self.wakeup = self.vehicle.get_wakeup_time()

        # _LOGGER.debug("API REG - {}".format(self.attributes.get("registrationNumber")))

        _LOGGER.debug("Status - {}".format(self.status))

        return True

    async def async_update_vehicle_health(self):
        # TODO: Add checking that it has been successful
        # by calling service status
        await self.vehicle.get_health_status()

    def get_odometer(self):
        if "Miles" in self.user_preferences:
            return int(self.status.get("ODOMETER_MILES"))
        else:
            return int(int(self.status.get("ODOMETER_METERS")) / 1000)

    def dist_to_user_prefs(self, kms: int) -> str:
        if "Miles" in self.user_preferences:
            return str(int(int(kms) * KMS_TO_MILES)) + LENGTH_MILES
        else:
            return str(kms) + LENGTH_KILOMETERS

    def temp_to_user_prefs(self, temp: int) -> str:
        if "Celsius" in self.user_preferences:
            return str(temp) + TEMP_CELSIUS
        else:
            return str((int(temp) * 1.8) + 32) + TEMP_FAHRENHEIT


class JLREntity(Entity):
    def __init__(self, data, sensor_type):
        """Create a new generic Dyson sensor."""
        self._name = None
        self._data = data
        self._sensor_type = sensor_type
        self._icon = "mid:cloud"
        self._entity_prefix = (
            self._data.attributes.get("vehicleBrand")
            + self._data.attributes.get("vehicleType")
            + "-"
            + self._data.vehicle.vin[-6]
            + "-"
        )

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
        return f"{self._entity_prefix}-{self._sensor_type}"

    async def async_update(self):
        _LOGGER.debug("Update requested")
        await self._data.async_update()
        return True

    async def async_added_to_hass(self):
        """Subscribe for update from the hub"""

        async def async_update_state():
            """Update sensor state."""
            await self.async_update_ha_state(True)

        async_dispatcher_connect(self.hass, SIGNAL_STATE_UPDATED, async_update_state)
