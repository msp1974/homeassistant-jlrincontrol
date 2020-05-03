"""
Jaguar Landrover Component for In Control API

Includes Sensor Devices and Services

https://github.com/msp1974/homeassistant-jlrincontrol.git
msparker@sky.com
"""
import asyncio
import json
import logging
from datetime import timedelta
from functools import partial

from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.helpers.event import (
    async_track_time_interval,
    async_call_later,
)
import jlrpy
import voluptuous as vol
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_TEMPERATURE,
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
from homeassistant.util import dt

from .const import (
    DOMAIN,
    KMS_TO_MILES,
    DEFAULT_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    DEFAULT_HEATH_UPDATE_INTERVAL,
    SIGNAL_STATE_UPDATED,
    JLR_SERVICES,
)
from .services import JLRService

# from homeassistant.helpers.icon import icon_for_battery_level

_LOGGER = logging.getLogger(__name__)

MIN_UPDATE_INTERVAL = timedelta(minutes=1)
DEFAULT_UPDATE_INTERVAL = timedelta(minutes=5)

CONF_DEBUG_DATA = "debug_data"
CONF_DISTANCE_UNIT = "distance_unit"
CONF_HEALTH_UPDATE_INTERVAL = "health_update_interval"

PLATFORMS = ["sensor", "lock", "device_tracker"]

ATTR_PIN = "pin"
ATTR_CHARGE_LEVEL = "max_charge_level"
ATTR_TARGET_VALUE = "target_value"
ATTR_TARGET_TEMP = "target_temp"

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

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Optional(CONF_DISTANCE_UNIT): vol.In(
                    [LENGTH_KILOMETERS, LENGTH_MILES]
                ),
                vol.Optional(CONF_DEBUG_DATA, default=False): cv.boolean,
                vol.Optional(CONF_PIN): cv.string,
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                ): (
                    vol.All(vol.Coerce(int), vol.Clamp(min=MIN_SCAN_INTERVAL))
                ),
                vol.Optional(
                    CONF_HEALTH_UPDATE_INTERVAL,
                    default=DEFAULT_HEATH_UPDATE_INTERVAL,
                ): vol.Coerce(int),
            }
        ),
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass, config):
    """Setup JLR InConnect component"""

    def get_schema(schema_list):
        s = {}
        for schema in schema_list:
            s.update(eval(schema))
        return vol.Schema(s)

    data = JLRApiHandler(hass, config)
    hass.data[DOMAIN] = data

    if await data.async_connect():
        if not data.connection.vehicles:
            # No vehicles or wrong credentials
            _LOGGER.error(
                "Unable to get vehicles from api.  Check credentials"
            )
            return False

        for vehicle in data.vehicles:
            for platform in PLATFORMS:
                hass.async_create_task(
                    async_load_platform(
                        hass,
                        platform,
                        DOMAIN,
                        data.vehicles[vehicle].vin,
                        config,
                    )
                )

        # Add services
        for service, service_info in JLR_SERVICES.items():
            _LOGGER.debug("Adding {} service".format(service))
            hass.services.async_register(
                DOMAIN,
                service,
                data.async_call_service,
                schema=get_schema(service_info.get("schema")),
            )

        # Schedule health update and repeat interval
        if data.health_update_interval > 0:
            _LOGGER.debug(
                "Scheduling vehicle health update on {} minute interval.  First call will be in 30 seconds.".format(
                    int(data.health_update_interval)
                )
            )

            # Do initial call to health_update service after HASS has started up.
            # This speeds up restart.
            # 30 seconds should do it.
            async_call_later(hass, 30, data.do_health_update)

            async_track_time_interval(
                hass,
                data.do_health_update,
                timedelta(minutes=data.health_update_interval),
            )
        else:
            _LOGGER.debug(
                "Scheduled vehicle health update is disabled.  Add to configuration.yaml to enable."
            )

    return True


class JLRApiHandler:
    def __init__(self, hass, config):
        self.hass = hass
        self.config = config[DOMAIN]
        self.connection = None
        self.vehicles = {}
        self.entities = []
        self.pin = self.config.get(CONF_PIN)
        self.update_interval = self.config.get(CONF_SCAN_INTERVAL)
        self.health_update_interval = self.config.get(
            CONF_HEALTH_UPDATE_INTERVAL
        )
        self.email = self.config.get(CONF_USERNAME)
        self.password = self.config.get(CONF_PASSWORD)

    @callback
    def do_status_update(self, *args):
        self.hass.async_create_task(self.async_update())

    @callback
    def do_health_update(self, *args):
        self.hass.async_create_task(self.async_health_update())

    async def async_connect(self):

        _LOGGER.debug("Creating connection to JLR InControl API")
        try:
            self.connection = await self.hass.async_add_executor_job(
                partial(jlrpy.Connection, self.email, self.password)
            )
        except Exception as ex:
            _LOGGER.warning(
                "Error connecting to JLRInControl.  Error is {}".format(ex)
            )
            return False

        _LOGGER.debug("Connected to API")

        # Discover all vehicles and get one time info
        for vehicle in self.connection.vehicles:
            _LOGGER.debug("Discovered vehicle - {}".format(vehicle.vin))
            # Get attributes
            vehicle.attributes = await self.hass.async_add_executor_job(
                vehicle.get_attributes
            )
            self.vehicles[vehicle.vin] = vehicle

            # Add one time dump of attr and status data for debugging
            if self.config.get(CONF_DEBUG_DATA):
                _LOGGER.debug("ATTRIBUTE DATA - {}".format(vehicle.attributes))
                status = await self.hass.async_add_executor_job(
                    vehicle.get_status
                )
                status = {
                    d["key"]: d["value"] for d in status["vehicleStatus"]
                }
                _LOGGER.debug("STATUS DATA - {}".format(status))

        # Get initial update and schedule interval update
        await self.async_update()

        _LOGGER.debug(
            "Scheduling update from InControl servers on {} minute interval".format(
                int(self.update_interval)
            )
        )
        async_track_time_interval(
            self.hass,
            self.do_status_update,
            timedelta(minutes=self.update_interval),
        )
        return True

    async def async_call_service(self, service):
        entity_id = service.data.get(ATTR_ENTITY_ID)
        entity = next(
            (
                entity
                for entity in self.hass.data[DOMAIN].entities
                if entity.entity_id == entity_id
            ),
            None,
        )

        # Get service info
        if entity and JLR_SERVICES[service.service]:
            vin = entity._vin
            kwargs = {}
            kwargs["service_name"] = JLR_SERVICES[service.service].get(
                "function_name"
            )
            kwargs["service_code"] = JLR_SERVICES[service.service].get(
                "service_code"
            )
            for k, v in service.data.items():
                kwargs[k] = v
            jlr_service = JLRService(self.hass, vin)
            status = await jlr_service.async_call_service(**kwargs)

            # Call update on return of monitorif successful
            if status and status == "Successful":
                _LOGGER.debug(
                    "Service call {} on vehicle {} successful. Updating entities from server.".format(
                        kwargs["service_name"],
                        self.vehicles[vin].attributes.get("nickname"),
                    )
                )
                await self.async_update()

    async def async_update(self):
        try:
            for vehicle in self.vehicles:
                status = await self.hass.async_add_executor_job(
                    self.vehicles[vehicle].get_status
                )
                last_updated = status.get("lastUpdatedTime")
                status = {
                    d["key"]: d["value"] for d in status["vehicleStatus"]
                }
                status["lastUpdatedTime"] = last_updated
                self.vehicles[vehicle].status = status

                self.vehicles[
                    vehicle
                ].position = await self.hass.async_add_executor_job(
                    self.vehicles[vehicle].get_position
                )

                trips = await self.hass.async_add_executor_job(
                    self.vehicles[vehicle].get_trips, 1
                )
                if trips:
                    self.vehicles[vehicle].last_trip = trips.get("trips")[0]

            _LOGGER.info("JLR InControl Update Received.")

            # Send update notice to all components to update
            async_dispatcher_send(self.hass, SIGNAL_STATE_UPDATED)
        except Exception as ex:
            _LOGGER.debug(
                "Unable to update from JLRInControl servers. They may be down or you have a internet connectivity issue.  Error is : {}".format(
                    ex
                )
            )

    async def async_health_update(self):
        try:
            for vehicle in self.vehicles:
                service = JLR_SERVICES["update_health_status"]
                kwargs = {}
                kwargs["service_name"] = service.get("function_name")
                kwargs["service_code"] = service.get("service_code")
                jlr_service = JLRService(self.hass, vehicle)
                await jlr_service.async_call_service(**kwargs)
            return True
        except Exception as ex:
            _LOGGER.debug(
                "Error when requesting health status update.  Error is {}".format(
                    ex
                )
            )


class JLREntity(Entity):
    def __init__(self, hass, vin):
        """Create a new generic JLR sensor."""
        self._hass = hass
        self._data = self._hass.data[DOMAIN]
        self._vin = vin
        self._vehicle = self._hass.data[DOMAIN].vehicles[self._vin]
        self._name = (
            self._vehicle.attributes.get("nickname")
            + " "
            + self._sensor_name.title()
        )
        self._fuel = self._vehicle.attributes.get("fuelType")
        self._entity_prefix = (
            self._vehicle.attributes.get("vehicleBrand")
            + self._vehicle.attributes.get("vehicleType")
            + "-"
            + self._vin[-6:]
        )

        _LOGGER.debug("Loading {} Sensors".format(self._name))

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
        return self._icon or "mdi:cloud"

    @property
    def vehicle(self):
        return self._vehicle

    @property
    def unique_id(self):
        """Return the sensor's unique id."""
        return f"{self._entity_prefix}-{self._sensor_name}"

    @property
    def assumed_state(self):
        """Return true if unable to access real state of entity."""
        return True

    async def async_update(self):
        _LOGGER.debug("Updating {}".format(self._name))
        return True

    async def async_added_to_hass(self):
        """Subscribe for update from the hub"""

        async def async_update_state():
            """Update sensor state."""
            await self.async_update_ha_state(True)

        async_dispatcher_connect(
            self.hass, SIGNAL_STATE_UPDATED, async_update_state
        )

    def to_local_datetime(self, datetime: str):
        try:
            return dt.as_local(dt.parse_datetime(datetime))
        except Exception:
            return None

    def get_distance_units(self):
        if self._data.config.get(CONF_DISTANCE_UNIT):
            return self._data.config.get(CONF_DISTANCE_UNIT)
        else:
            return self.hass.config.units.length_unit

    def get_odometer(self, vehicle):
        self.units = self.get_distance_units()
        if self.units == LENGTH_KILOMETERS:
            return int(int(vehicle.status.get("ODOMETER_METER")) / 1000)
        else:
            return int(vehicle.status.get("ODOMETER_MILES"))
