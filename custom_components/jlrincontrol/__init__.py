"""
Jaguar Landrover Component for In Control API

Includes Sensor Devices and Services

https://github.com/msp1974/homeassistant-jlrincontrol.git
msparker@sky.com
"""

import json
import asyncio
import logging
from datetime import timedelta

import homeassistant.helpers.config_validation as cv
import jlrpy
import voluptuous as vol
from homeassistant.const import (
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PIN,
    CONF_RESOURCES,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    LENGTH_KILOMETERS,
    LENGTH_MILES,
    PRESSURE_PSI,
    TEMP_CELSIUS,
    TEMP_FAHRENHEIT,
)
from homeassistant.core import callback
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, KMS_TO_MILES, SCAN_INTERVAL, SIGNAL_STATE_UPDATED

# from homeassistant.helpers.entity import Entity
# from homeassistant.helpers.dispatcher import dispatcher_send
# from homeassistant.helpers.icon import icon_for_battery_level

_LOGGER = logging.getLogger(__name__)

MIN_UPDATE_INTERVAL = timedelta(minutes=1)
DEFAULT_UPDATE_INTERVAL = timedelta(minutes=5)

CONF_DEBUG_DATA = "debug_data"

PLATFORMS = ["sensor", "lock", "device_tracker"]

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Optional(CONF_DEBUG_DATA, default=False): cv.boolean,
                vol.Optional(CONF_PIN): cv.string,
                vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): (
                    vol.All(cv.time_period, vol.Clamp(min=MIN_UPDATE_INTERVAL))
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
    hass.data[DOMAIN] = data

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
        self.timer_handle = None
        self.user_preferences = {
            "timeZone": "Europe/London",
            "unitsOfMeasurement": "Miles Litres Celsius DistPerVol kWhPer100Dist kWh",
            "dateFormat": "DD/MM/YYYY",
            "language": "en_GB",
        }

        _LOGGER.debug("Creating connection to JLR InControl API")
        self.connection = jlrpy.Connection(
            email=self.config[DOMAIN].get(CONF_USERNAME),
            password=self.config[DOMAIN].get(CONF_PASSWORD),
        )

        # Get one time info
        self.vehicle = self.connection.vehicles[0]
        self.attributes = self.vehicle.get_attributes()

        # Add one time dump of attr and status data for debugging
        if self.config[DOMAIN].get(CONF_DEBUG_DATA):
            _LOGGER.debug("ATTRIBUTE DATA - {}".format(self.attributes))
            status = self.vehicle.get_status()
            self.status = {d["key"]: d["value"] for d in status["vehicleStatus"]}
            _LOGGER.debug("STATUS DATA - {}".format(self.status))

        # Get user preferences - inconsistant return of data - retry until fetched (max 10 times)
        for i in range(10):
            _LOGGER.debug("Requesting user preferences iteration {}".format(i + 1))
            u = self.connection.get_user_info()
            # Check for user prefs info
            if u.get("contact").get("userPreferences"):
                self.user_preferences = u.get("contact").get("userPreferences")
                _LOGGER.debug("Requested user preferences returned.")
                break
            # Pause between requests
            asyncio.sleep(0.2)

        _LOGGER.debug("User Preferences - {}".format(self.user_preferences))

    @callback
    def do_status_update(self):
        self._hass.async_create_task(self.async_update())

    @callback
    def schedule_next_health_update(self):
        self._hass.async_create_task(self.async_update())

    async def async_update(self):
        self.position = self.vehicle.get_position()
        status = self.vehicle.get_status()
        self.status = {d["key"]: d["value"] for d in status["vehicleStatus"]}
        self.status["lastUpdatedTime"] = status.get("lastUpdatedTime")

        # Wakeup may not be available on all models - issue #1
        try:
            self.wakeup = self.vehicle.get_wakeup_time()
        except Exception as ex:
            _LOGGER.debug("Unable to get wakeup info.  Error is {}".format(ex))
            self.wakeup = None

        # Schedule next update
        self.timer_handle = self._hass.loop.call_later(
            SCAN_INTERVAL, self.do_status_update
        )

        _LOGGER.info("JLR InControl Update Received")
        # Send update notice to all components to update
        async_dispatcher_send(self._hass, SIGNAL_STATE_UPDATED)

        return True

    async def async_update_vehicle_health(self):
        # TODO: Add checking that it has been successful
        # by calling service status
        await self.vehicle.get_health_status()

    def get_odometer(self):
        if "Miles" in self.user_preferences.get("unitsOfMeasurement"):
            return int(self.status.get("ODOMETER_MILES"))
        else:
            return int(int(self.status.get("ODOMETER_METER")) / 1000)

    def dist_to_user_prefs(self, kms: int) -> str:
        if "Miles" in self.user_preferences.get("unitsOfMeasurement"):
            return int(int(kms) * KMS_TO_MILES)
        else:
            return kms

    def temp_to_user_prefs(self, temp: int) -> str:
        if "Celsius" in self.user_preferences.get("unitsOfMeasurement"):
            return str(temp) + TEMP_CELSIUS
        else:
            return str((int(temp) * 1.8) + 32) + TEMP_FAHRENHEIT

    # TODO: vol_to_user_prefs

    """
    --------------------------------------------------
    Services Functions
    --------------------------------------------------
    """

    async def async_start_vehicle(self, pin, temp=20):
        result = await self._hass.async_add_executor_job(
            self.vehicle.remote_engine_start(pin, temp)
        )
        return result

    async def async_stop_vehicle(self, pin):
        result = await self._hass.async_add_executor_job(
            self.vehicle.remote_engine_stop(pin)
        )
        return result

    async def async_reset_alarm(self, pin):
        result = await self._hass.async_add_executor_job(self.vehicle.reset_alarm(pin))
        return result

    async def async_honk_blink(self, pin):
        result = await self._hass.async_add_executor_job(self.vehicle.honk_blink())
        return result


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
        _LOGGER.debug("Updating {}".format(self._name))
        return True

    async def async_added_to_hass(self):
        """Subscribe for update from the hub"""

        async def async_update_state():
            """Update sensor state."""
            await self.async_update_ha_state(True)

        async_dispatcher_connect(self.hass, SIGNAL_STATE_UPDATED, async_update_state)
