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
from typing import Optional

from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.helpers.event import (
    async_track_time_interval,
    async_call_later,
)
import jlrpy
import voluptuous as vol
from homeassistant import config_entries
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
    PRESSURE_BAR,
    PRESSURE_PA,
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
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt

from .const import (
    DOMAIN,
    DATA_JLR_CONFIG,
    KMS_TO_MILES,
    DEFAULT_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    DEFAULT_HEATH_UPDATE_INTERVAL,
    SIGNAL_STATE_UPDATED,
    JLR_SERVICES,
    JLR_DATA,
)
from .services import JLRService
from .util import mask

# from homeassistant.helpers.icon import icon_for_battery_level

_LOGGER = logging.getLogger(__name__)

MIN_UPDATE_INTERVAL = timedelta(minutes=1)
DEFAULT_UPDATE_INTERVAL = timedelta(minutes=5)

HEALTH_UPDATE_TRACKER = "health_update_tracker"
STATUS_UPDATE_TRACKER = "status_update_tracker"

CONF_DEBUG_DATA = "debug_data"
CONF_DISTANCE_UNIT = "distance_unit"
CONF_PRESSURE_UNIT = "pressure_unit"
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
                vol.Optional(CONF_PRESSURE_UNIT): vol.In(
                    [PRESSURE_BAR, PRESSURE_PSI]
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
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass, config):
    """
    JLR InControl uses config flow for configuration.

    But, a "jlrincontrol:" entry in configuration.yaml will trigger an import flow
    if a config entry doesn't already exist. If it exists, the import
    flow will attempt to import it and create a config entry, to assist users
    migrating from the old jlrincontrol component. Otherwise, the user will have to
    continue setting up the integration via the config flow.
    """
    jlr_config: Optional[ConfigType] = config.get(DOMAIN)
    hass.data.setdefault(DOMAIN, {})

    if not jlr_config:
        return True

    # Import config if doesn't already exist
    config_entry = _async_find_matching_config_entry(hass)
    if not config_entry:
        """
        No config entry exists and configuration.yaml config exists,
        so lets trigger the import flow.
        """
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": config_entries.SOURCE_IMPORT},
                data=dict(jlr_config),
            )
        )
        return True

    # Update the entry based on the YAML configuration, in case it changed.
    # hass.config_entries.async_update_entry(config_entry, data=dict(jlr_config))
    return True


@callback
def _async_find_matching_config_entry(hass):
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.source == config_entries.SOURCE_IMPORT:
            return entry


async def async_setup_entry(hass, config_entry):
    """Setup JLR InConnect component"""
    _async_import_options_from_data_if_missing(hass, config_entry)

    def get_schema(schema_list):
        s = {}
        for schema in schema_list:
            s.update(eval(schema))
        return vol.Schema(s)

    hass.data[DOMAIN][config_entry.entry_id] = {}
    hass_jlr_data = hass.data[DOMAIN][config_entry.entry_id]

    config_entry.add_update_listener(_async_update_listener)

    data = JLRApiHandler(hass, config_entry)
    hass_jlr_data[JLR_DATA] = data

    if await data.async_connect():
        if not data.connection.vehicles:
            # No vehicles or wrong credentials
            _LOGGER.error(
                "Unable to get vehicles from api.  Check credentials"
            )
            return False

        await async_update_device_registry(
            hass, config_entry, data.connection.vehicles, data
        )

        # for vehicle in data.vehicles:
        for platform in PLATFORMS:
            hass.async_create_task(
                hass.config_entries.async_forward_entry_setup(
                    config_entry, platform
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
        if data.health_update_interval and data.health_update_interval > 0:
            _LOGGER.debug(
                "Scheduling vehicle health update on {} minute interval.  First call will be in 30 seconds.".format(
                    int(data.health_update_interval)
                )
            )

            # Do initial call to health_update service after HASS has started up.
            # This speeds up restart.
            # 30 seconds should do it.
            async_call_later(hass, 30, data.do_health_update)

            hass_jlr_data[HEALTH_UPDATE_TRACKER] = async_track_time_interval(
                hass,
                data.do_health_update,
                timedelta(minutes=data.health_update_interval),
            )
        else:
            _LOGGER.debug(
                "Scheduled vehicle health update is disabled.  Add to configuration.yaml to enable."
            )

    return True


@callback
def _async_import_options_from_data_if_missing(hass, config_entry):
    options = dict(config_entry.options)
    modified = False
    for importable_option in [
        CONF_PIN,
        CONF_DISTANCE_UNIT,
        CONF_PRESSURE_UNIT,
        CONF_SCAN_INTERVAL,
        CONF_HEALTH_UPDATE_INTERVAL,
        CONF_DEBUG_DATA,
    ]:
        if (
            importable_option not in config_entry.options
            and importable_option in config_entry.data
        ):
            options[importable_option] = config_entry.data[importable_option]
            modified = True

    if modified:
        hass.config_entries.async_update_entry(config_entry, options=options)


async def _async_update_listener(hass, config_entry):
    """Handle options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_update_device_registry(hass, config_entry, vehicles, data):
    """Update device registry."""
    device_registry = await hass.helpers.device_registry.async_get_registry()
    for vehicle in vehicles:
        device_registry.async_get_or_create(
            config_entry_id=config_entry.entry_id,
            connections={},
            identifiers={(DOMAIN, vehicle.vin)},
            manufacturer=data.vehicles[vehicle.vin].attributes.get(
                "vehicleBrand"
            ),
            name=data.vehicles[vehicle.vin].attributes.get("nickname"),
            model=data.vehicles[vehicle.vin].attributes.get("vehicleType"),
            sw_version="1.0",
        )


async def async_unload_entry(hass, config_entry):
    """Unload a config entry."""
    _LOGGER.debug("Unloading JLR InControl Component")
    hass_jlr_data = hass.data[DOMAIN][config_entry.entry_id]

    # Stop scheduled update
    if hass_jlr_data.get(STATUS_UPDATE_TRACKER):
        hass_jlr_data[STATUS_UPDATE_TRACKER]()
        hass_jlr_data[STATUS_UPDATE_TRACKER] = None

    if hass_jlr_data.get(HEALTH_UPDATE_TRACKER):
        hass_jlr_data[HEALTH_UPDATE_TRACKER] = None

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
        # Deregister services
        _LOGGER.debug("Unregister JLR InControl Services")
        for service, service_info in JLR_SERVICES.items():
            _LOGGER.debug("Unregister {}".format(service))
            hass.services.async_remove(DOMAIN, service)
        hass.data[DOMAIN].pop(config_entry.entry_id)

    return unload_ok


class JLRApiHandler:
    def __init__(self, hass, config_entry):
        self.hass = hass
        self.config_entry = config_entry
        self.connection = None
        self.email = config_entry.data.get(CONF_USERNAME)
        self.password = config_entry.data.get(CONF_PASSWORD)
        self.vehicles = {}
        self.entities = []
        self.pin = config_entry.options.get(CONF_PIN)
        self.distance_unit = config_entry.options.get(CONF_DISTANCE_UNIT)
        self.pressure_unit = config_entry.options.get(CONF_PRESSURE_UNIT)
        self.update_interval = config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        self.health_update_interval = config_entry.options.get(
            CONF_HEALTH_UPDATE_INTERVAL
        )

        self.debug_data = config_entry.options.get(CONF_DEBUG_DATA)

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
            _LOGGER.debug(
                "Discovered vehicle - {}".format(mask(vehicle.vin, 3, 2))
            )
            # Get attributes
            vehicle.attributes = await self.hass.async_add_executor_job(
                vehicle.get_attributes
            )
            self.vehicles[vehicle.vin] = vehicle

            # Add one time dump of attr and status data for debugging
            if self.debug_data:
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
        self.hass.data[DOMAIN][self.config_entry.entry_id][
            STATUS_UPDATE_TRACKER
        ] = async_track_time_interval(
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
                for entity in self.hass.data[DOMAIN][
                    self.config_entry.entry_id
                ][JLR_DATA].entities
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
            jlr_service = JLRService(self.hass, self.config_entry, vin)
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
                _LOGGER.debug(
                    "Received status data update for {}".format(
                        self.vehicles[vehicle].attributes.get("nickname")
                    )
                )
                status["lastUpdatedTime"] = last_updated
                self.vehicles[vehicle].status = status

                position = await self.hass.async_add_executor_job(
                    self.vehicles[vehicle].get_position
                )

                if position:
                    self.vehicles[vehicle].position = position
                    _LOGGER.debug(
                        "Received position data update for {}".format(
                            self.vehicles[vehicle].attributes.get("nickname")
                        )
                    )
                else:
                    self.vehicles[vehicle].position = None
                    _LOGGER.debug(
                        "No position data received for {}".format(
                            self.vehicles[vehicle].attributes.get("nickname")
                        )
                    )

                # Only get trip data if privacy mode is not enabled
                if status.get("PRIVACY_SWITCH") == "FALSE":
                    trips = await self.hass.async_add_executor_job(
                        self.vehicles[vehicle].get_trips, 1
                    )
                    if trips and trips.get("trips"):
                        self.vehicles[vehicle].last_trip = trips.get("trips")[
                            0
                        ]
                        _LOGGER.debug(
                            "Retieved trip data update for {}".format(
                                self.vehicles[vehicle].attributes.get(
                                    "nickname"
                                )
                            )
                        )
                    else:
                        self.vehicles[vehicle].last_trip = None
                        _LOGGER.debug(
                            "No trip data received for {}".format(
                                self.vehicles[vehicle].attributes.get(
                                    "nickname"
                                )
                            )
                        )
                else:
                    self.vehicles[vehicle].last_trip = None
                    _LOGGER.debug(
                        "Privacy mode is enabled. Trip data will not be loaded for {}".format(
                            self.vehicles[vehicle].attributes.get("nickname")
                        )
                    )

            _LOGGER.info(
                "JLR InControl update received for {}".format(
                    self.vehicles[vehicle].attributes.get("nickname")
                )
            )

            # Send update notice to all components to update
            async_dispatcher_send(self.hass, SIGNAL_STATE_UPDATED)
        except Exception as ex:
            _LOGGER.debug(
                "Unable to update data from JLRInControl servers. They may be down or you have a internet connectivity issue.  Error is : {}".format(
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
