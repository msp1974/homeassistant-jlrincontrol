"""Handles updating data from jlrpy"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import jlrpy
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_PASSWORD,
    CONF_PIN,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    UnitOfEnergy,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .services import JLRService
from .util import field_mask
from .const import (
    CONF_DISTANCE_UNIT,
    CONF_HEALTH_UPDATE_INTERVAL,
    CONF_PRESSURE_UNIT,
    CONF_USE_CHINA_SERVERS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    FUEL_TYPE_BATTERY,
    FUEL_TYPE_HYBRID,
    FUEL_TYPE_ICE,
    JLR_DATA,
    JLR_SERVICES,
    JLR_TO_HASS_UNITS,
    VERSION,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class UserPreferenceUnits:
    """Holds unit prefs"""

    distance: str
    fuel: str
    temp: str
    pressure: str
    energy_regenerated: str
    energy_consumed: str


@dataclass
class UserData:
    """Holds user data"""

    first_name: str
    middle_name: str
    last_name: str
    user_preferences: UserPreferenceUnits = field(default_factory=dict)


@dataclass
class VehicleData:
    """Hold vehicle data"""

    vin: str
    name: str = ""
    engine_type: str = "Unknown"
    fuel: str = "Unknown"
    last_updated: datetime = None
    position: dict = field(default_factory=dict)
    attributes: dict = field(default_factory=dict)
    supported_services: list = field(default_factory=list)
    status: dict = field(default_factory=dict)
    status_ev: dict = field(default_factory=dict)
    last_trip: dict = field(default_factory=dict)
    trips: dict = field(default_factory=dict)


class JLRIncontrolUpdateCoordinator(DataUpdateCoordinator):
    """Update handler"""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize data update coordinator."""

        self.hass = hass
        self.connection: jlrpy.Connection = None
        self.user: UserData
        self.email = config_entry.data.get(CONF_USERNAME)
        self.password = config_entry.data.get(CONF_PASSWORD)
        self.use_china_servers = config_entry.data.get(CONF_USE_CHINA_SERVERS)
        self.vehicles: dict[str, VehicleData] = {}
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

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} ({config_entry.unique_id})",
            update_method=self.async_update_data,
            update_interval=timedelta(minutes=self.update_interval),
        )

    async def async_connect(self) -> bool:
        """Connnect to api"""
        _LOGGER.debug("Initialising JLR InControl v%s", VERSION)
        _LOGGER.debug("Creating connection to JLR InControl API")
        try:
            self.connection = await self.hass.async_add_executor_job(
                jlrpy.Connection,
                self.email,
                self.password,
                "",
                "",
                self.use_china_servers,
            )
            await self.async_get_user_info()
            await self.async_get_vehicles()
            _LOGGER.debug("Connected to API")

            for vehicle in self.connection.vehicles:
                await self.async_get_vehicle_attributes(vehicle)

        except Exception as ex:
            _LOGGER.warning(
                "Error connecting to JLRInControl.  Error is %s", ex
            )
            return False
        return True

    async def async_get_user_info(self) -> None:
        """Get user info"""
        user = (
            await self.hass.async_add_executor_job(
                self.connection.get_user_info
            )
        ).get("contact")

        uoms = str(
            user.get("userPreferences", {}).get("unitsOfMeasurement", "")
        ).split(" ")
        try:
            user_prefs = UserPreferenceUnits(
                distance=JLR_TO_HASS_UNITS.get(
                    uoms[0], self.hass.config.units.length_unit
                ),
                fuel=JLR_TO_HASS_UNITS.get(
                    uoms[1], self.hass.config.units.volume_unit
                ),
                temp=JLR_TO_HASS_UNITS.get(
                    uoms[2], self.hass.config.units.temperature_unit
                ),
                pressure=self.hass.config.units.pressure_unit,
                energy_regenerated=JLR_TO_HASS_UNITS.get(
                    uoms[4], UnitOfEnergy.KILO_WATT_HOUR
                ),
                energy_consumed=uoms[5],
            )
        except IndexError:
            user_prefs = UserPreferenceUnits(
                distance=self.hass.config.units.length_unit,
                fuel=self.hass.config.units.volume_unit,
                temp=self.hass.config.units.temperature_unit,
                pressure=self.hass.config.units.pressure_unit,
                energy_regenerated=UnitOfEnergy.KILO_WATT_HOUR,
                energy_consumed="Unknown",
            )

        self.user = UserData(
            first_name=user.get("firstName", "Unkown"),
            middle_name=user.get("middleName", "Unknown"),
            last_name=user.get("lastName", "Unknown"),
            user_preferences=user_prefs,
        )

        _LOGGER.debug("User Data: %s", self.user)

    async def async_get_vehicles(self) -> None:
        """Get list of vehicles"""
        if len(self.connection.vehicles) > 0:
            _LOGGER.debug("Vehicles: %s", json.dumps(self.connection.vehicles))
            for vehicle in self.connection.vehicles:
                vehicle_data = VehicleData(vin=vehicle.vin)
                self.vehicles[vehicle.vin] = vehicle_data
        else:
            _LOGGER.debug("No vehicles found in this account")

    async def async_get_vehicle_attributes(
        self, vehicle: jlrpy.Vehicle
    ) -> None:
        """Get vehicle attributes"""
        attributes = await self.hass.async_add_executor_job(
            vehicle.get_attributes
        )

        if attributes:
            _LOGGER.debug(
                "Retrieved attribute data for %s",
                field_mask(vehicle.vin, 3, 2),
            )
            self.vehicles[vehicle.vin].attributes = attributes
            self.vehicles[vehicle.vin].fuel = attributes.get("fuelType")
            self.get_vehicle_engine_type(self.vehicles[vehicle.vin])

            # Set supported services
            self.vehicles[vehicle.vin].supported_services = [
                service.get("serviceType")
                for service in attributes.get("availableServices")
                if service.get("vehicleCapable")
                and service.get("serviceEnabled")
            ]

            # Add privacy mode, service mode and transport mode support
            self.vehicles[vehicle.vin].supported_services.append(
                ["PM", "SM", "TM"]
            )

        else:
            _LOGGER.debug(
                "Attribute data is empty for %s",
                field_mask(vehicle.vin, 3, 2),
            )

    async def async_get_vehicle_status(self, vehicle: jlrpy.Vehicle) -> None:
        """Get vehicle status"""
        status = await self.hass.async_add_executor_job(vehicle.get_status)

        if status:
            _LOGGER.debug(
                "Retrieved status data for %s",
                field_mask(vehicle.vin, 3, 2),
            )
            if status["vehicleStatus"].get("coreStatus"):
                self.vehicles[vehicle.vin].status = {
                    d["key"]: d["value"]
                    for d in status["vehicleStatus"]["coreStatus"]
                }
                self.vehicles[vehicle.vin].last_updated = status.get(
                    "lastUpdatedTime"
                )

            if status["vehicleStatus"].get("evStatus"):
                self.vehicles[vehicle.vin].status_ev = {
                    d["key"]: d["value"]
                    for d in status["vehicleStatus"]["evStatus"]
                }
        else:
            _LOGGER.debug(
                "Status data is empty for %s",
                field_mask(vehicle.vin, 3, 2),
            )

    def get_vehicle_engine_type(self, vehicle: VehicleData) -> None:
        """Determine vehicle engine type"""
        _LOGGER.debug(
            "Vehicle fuel type is %s",
            vehicle.attributes.get("fuelType", "Unknown"),
        )

        if vehicle.attributes.get("fuelType") == FUEL_TYPE_BATTERY:
            self.vehicles[vehicle.vin].engine_type = FUEL_TYPE_BATTERY
        elif vehicle.status_ev and vehicle.status_ev.get(
            "EV_PHEV_RANGE_COMBINED_KM"
        ):
            self.vehicles[vehicle.vin].engine_type = FUEL_TYPE_HYBRID
        else:
            self.vehicles[vehicle.vin].engine_type = FUEL_TYPE_ICE

    async def async_get_vehicle_position(self, vehicle: jlrpy.Vehicle) -> None:
        """Get vehicle position data"""
        position = await self.hass.async_add_executor_job(vehicle.get_position)

        if position:
            self.vehicles[vehicle.vin].position = position
            _LOGGER.debug(
                "Received position data update for %s",
                self.vehicles[vehicle.vin].attributes.get("nickname"),
            )
        else:
            self.vehicles[vehicle.vin].position = None
            _LOGGER.debug(
                "No position data received for %s",
                self.vehicles[vehicle.vin].attributes.get("nickname"),
            )

    async def async_get_vehicle_last_trip_data(
        self, vehicle: jlrpy.Vehicle
    ) -> None:
        """Get vehicle trip data"""

        trips = await self.hass.async_add_executor_job(vehicle.get_trips, 1)
        if trips and trips.get("trips"):
            self.vehicles[vehicle.vin].last_trip = trips.get("trips")[0]
            _LOGGER.debug(
                "Retieved trip data update for %s",
                self.vehicles[vehicle.vin].attributes.get("nickname"),
            )
        else:
            self.vehicles[vehicle.vin].last_trip = None
            _LOGGER.debug(
                "No trip data received for %s",
                self.vehicles[vehicle.vin].attributes.get("nickname"),
            )

    async def async_update_data(self):
        """Update vehicle data"""
        try:
            for vehicle in self.connection.vehicles:
                await self.async_get_vehicle_status(vehicle)
                await self.async_get_vehicle_position(vehicle)

                if (
                    self.vehicles[vehicle.vin].status.get("PRIVACY_SWITCH")
                    == "FALSE"
                ):
                    await self.async_get_vehicle_last_trip_data(vehicle)
                else:
                    self.vehicles[vehicle.vin].last_trip = None
                    _LOGGER.debug(
                        "Privacy mode is enabled. Trip data not loaded for %s",
                        self.vehicles[vehicle.vin].attributes.get("nickname"),
                    )

                _LOGGER.info(
                    "JLR InControl update received for %s",
                    self.vehicles[vehicle.vin].attributes.get("nickname"),
                )
            return True

        except Exception as ex:
            msg = (
                f"Unable to update data from JLRInControl servers. "
                f"Error is: {ex}"
            )
            _LOGGER.debug(msg)
            return False

    async def async_health_update(self):
        """Request update from vehicle"""
        try:
            for vehicle in self.vehicles:
                service = JLR_SERVICES["update_health_status"]
                kwargs = {}
                kwargs["service_name"] = service.get("function_name")
                kwargs["service_code"] = service.get("service_code")
                jlr_service = JLRService(self.hass, self.config_entry, vehicle)
                await jlr_service.async_call_service(**kwargs)
            return True
        except Exception as ex:
            _LOGGER.debug(
                "Error when requesting health status update. Error is %s",
                ex,
            )

    async def async_call_service(self, service):
        """Handle service call"""
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
            vin = entity.vin
            kwargs = {}
            kwargs["service_name"] = JLR_SERVICES[service.service].get(
                "function_name"
            )
            kwargs["service_code"] = JLR_SERVICES[service.service].get(
                "service_code"
            )
            for key, value in service.data.items():
                kwargs[key] = value
            jlr_service = JLRService(self.hass, self.config_entry, vin)
            status = await jlr_service.async_call_service(**kwargs)

            if status and status == "Successful":
                _LOGGER.debug(
                    "Service call %s on vehicle %s successful. ",
                    kwargs["service_name"],
                    self.vehicles[vin].attributes.get("nickname"),
                )
            # Call update on return of monitor
            await self.async_update_data()
