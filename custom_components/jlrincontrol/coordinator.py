"""Handles updating data from jlrpy."""
import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import logging
from urllib.error import HTTPError

from aiojlrpy import (
    Connection,
    JLRServices,
    StatusMessage,
    Vehicle,
    VehicleStatus,
    process_vhs_message,
)
from aiojlrpy.exceptions import JLRException

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_PIN,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    UnitOfEnergy,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_call_later, async_track_time_interval
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_DEFAULT_CLIMATE_TEMP,
    CONF_DEFAULT_SERVICE_DURATION,
    CONF_DEVICE_ID,
    CONF_HEALTH_UPDATE_INTERVAL,
    CONF_PRESSURE_UNIT,
    CONF_USE_CHINA_SERVERS,
    DEFAULT_SCAN_INTERVAL,
    DEPRECATED_SERVICES,
    DOMAIN,
    JLR_SERVICES,
    JLR_TO_HASS_UNITS,
    VERSION,
    PowerTrainType,
)
from .services import JLRService
from .util import (
    debug_log_status,
    field_mask,
    get_is_date_active,
    get_user_prefs,
    get_value_match,
    save_user_prefs,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class UserPreferenceUnits:
    """Holds unit prefs."""

    distance: str
    fuel: str
    temp: str
    pressure: str
    energy_regenerated: str
    energy_consumed: str

    def to_json(self):
        """Convert to json."""
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True)


@dataclass
class UserData:
    """Holds user data."""

    first_name: str
    middle_name: str
    last_name: str
    user_preferences: UserPreferenceUnits = field(default_factory=UserPreferenceUnits)
    user_prefs_from_account: bool = False


@dataclass
class GuardianData:
    """Holds guardian mode data."""

    capable: bool = True
    active: bool = False
    expiry: str = "0"


@dataclass
class TrackedStatuses:
    """Holds tracked status info."""

    climate_engine_active: bool = False
    climate_electric_active: bool = False
    guardian_mode_active: bool = False
    is_charging: bool = False
    privacy_mode_enabled: bool = False
    transport_mode_enabled: bool = False
    service_mode_enabled: bool = False


@dataclass
class VehicleData:
    """Hold vehicle data."""

    vin: str
    api: Vehicle
    name: str = ""
    engine_type: str = "Unknown"
    fuel: str = "Unknown"
    last_updated: datetime = None
    last_status_update: datetime = None
    position: dict = field(default_factory=dict)
    attributes: dict = field(default_factory=dict)
    supported_services: list = field(default_factory=list)
    status: VehicleStatus = field(default_factory=VehicleStatus)
    guardian_mode: dict = field(default_factory=dict)
    tracked_status: TrackedStatuses = field(default_factory=TrackedStatuses)
    last_trip: dict = field(default_factory=dict)
    trips: dict = field(default_factory=dict)
    target_climate_temp: int = 21
    short_interval_monitor: bool = False


class JLRIncontrolHealthUpdateCoordinator(DataUpdateCoordinator):
    """Update handler."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        coordinator: DataUpdateCoordinator,
    ) -> None:
        """Initialize data update coordinator."""

        self.hass = hass
        self.coordinator = coordinator
        self.config_entry = config_entry
        self.connection: Connection = coordinator.connection
        self.health_update_interval = config_entry.options.get(
            CONF_HEALTH_UPDATE_INTERVAL, 0
        )

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} ({config_entry.unique_id}-HU)",
            update_method=self.async_update_data,
            update_interval=timedelta(minutes=self.health_update_interval),
        )

        _LOGGER.debug(
            "Health Update Init on %d min interval", self.health_update_interval
        )

    async def async_update_data(self):
        """Request update from vehicle."""
        try:
            for vehicle in self.connection.vehicles:
                _LOGGER.debug(
                    "Requesting health update from %s",
                    self.coordinator.vehicles[vehicle.vin].name,
                )
                jlr_service = JLRService(
                    self.coordinator, vehicle.vin, "update_health_status"
                )
                success = await jlr_service.async_call_service()
                if success:
                    _LOGGER.debug(
                        "Health update successful for %s",
                        self.coordinator.vehicles[vehicle.vin].name,
                    )
        except HTTPError as ex:
            _LOGGER.debug(
                "Error when requesting health status update. Error is %s",
                ex,
            )


class JLRIncontrolUpdateCoordinator(DataUpdateCoordinator):
    """Update handler."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize data update coordinator."""

        self.hass = hass
        self.config_entry = config_entry
        self.connection: Connection
        self.user: UserData
        self.email = config_entry.data.get(CONF_USERNAME)
        self.password = config_entry.data.get(CONF_PASSWORD)
        self.use_china_servers = config_entry.data.get(CONF_USE_CHINA_SERVERS)
        self.device_id = config_entry.data.get(CONF_DEVICE_ID)
        self.vehicles: dict[str, VehicleData] = {}
        self.entities = []
        self.pin = (
            config_entry.data.get(CONF_PIN)
            if config_entry.data.get(CONF_PIN) != "0000"
            else None
        )
        self.pressure_unit = config_entry.options.get(CONF_PRESSURE_UNIT, "Default")
        self.default_climate_temp = config_entry.options.get(
            CONF_DEFAULT_CLIMATE_TEMP, 21
        )
        self.default_service_duration = config_entry.options.get(
            CONF_DEFAULT_SERVICE_DURATION, 24
        )
        self.scan_interval = config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        self.health_update_interval = config_entry.options.get(
            CONF_HEALTH_UPDATE_INTERVAL
        )

        self.scheduled_update_task: asyncio.Task = None
        self.short_interval_monitor_task: asyncio.Task = None

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} ({config_entry.unique_id})",
            update_method=self.async_update_data,
            update_interval=timedelta(minutes=self.scan_interval),
        )

    async def monitored_vehicle_status(self, interval: int):
        """Get vehicle status."""
        while True:
            await asyncio.sleep(interval)
            for _, vehicle in self.vehicles.items():
                if vehicle.short_interval_monitor:
                    _LOGGER.debug(
                        "Calling monitoring update status for %s", vehicle.name
                    )
                    await self.async_status_only_update(vehicle)

    async def _on_ws_message(self, message: StatusMessage):
        """Websocket message callback function."""
        _LOGGER.debug(message)
        if self.vehicles:
            if message.service == JLRServices.GUARDIAN_MODE:
                if message.vin:
                    data = json.loads(message.data.get("b"))
                    self.vehicles[message.vin].guardian_mode = data
                    self.vehicles[message.vin].tracked_status.guardian_mode_active = (
                        True if data["status"] == "ACTIVE" else False
                    )
            if message.service == JLRServices.VEHICLE_HEALTH:
                if message.vin:
                    if data := message.data.get("b"):
                        json_data = json.loads(message.data.get("b"))
                        status = process_vhs_message(json_data)
                        debug_log_status(status)
                        self.identify_status_changes(self.vehicles[message.vin], status)
                        self.vehicles[message.vin].status = status
                        await self.get_tracked_statuses(self.vehicles[message.vin])
                        # Just had VHS message so cancel any outstanding status updates
                        if self.scheduled_update_task:
                            self.scheduled_update_task.cancel()

            if (
                message.service
                in [
                    JLRServices.REMOTE_DOOR_LOCK,
                    JLRServices.REMOTE_DOOR_UNLOCK,
                    JLRServices.REMOTE_ENGINE_ON,
                    JLRServices.REMOTE_ENGINE_OFF,
                    JLRServices.ELECTRIC_CLIMATE_CONTROL,
                ]
                and message.vin
            ):
                # Schedule status update in case VHS message doesn't come
                self.scheduled_update_task = asyncio.create_task(
                    self.get_delayed_vehicle_status(self.vehicles[message.vin], 15)
                )

            self.hass.async_add_executor_job(self.async_update_listeners)

    async def async_connect(self) -> bool:
        """Connnect to api."""
        _LOGGER.debug("Initialising JLR InControl v%s", VERSION)
        _LOGGER.debug("Creating connection to JLR InControl API")
        try:
            self.connection = Connection(
                self.email,
                self.password,
                self.device_id,
                "",
                self.use_china_servers,
                self._on_ws_message,
                websocket_auto_connect=False,
            )
            await self.connection.connect()
            await self.async_get_vehicles()
            await self.async_get_user_info()

            _LOGGER.debug("Connected to API")

            for _, vehicle in self.vehicles.items():
                await self.async_get_vehicle_attributes(vehicle)

            _LOGGER.debug("Connecting to websocket api")
            self.hass.create_task(self.connection.websocket_connect())

            _LOGGER.debug("Setting up vehicle monitoring job")
            self.hass.async_create_background_task(
                self.monitored_vehicle_status(60), "JLR Status Polling"
            )

        except JLRException as ex:
            _LOGGER.warning("Error connecting to JLRInControl.  Error is %s", ex)
            return False
        return True

    async def async_get_user_info(self) -> None:
        """Get user info."""
        if not self.connection.user:
            user = await self.connection.get_user_info()
        else:
            user = self.connection.user

        _LOGGER.debug("USERINFO: %s", user)
        user = user.get("contact")

        received_uoms = str(
            user.get("userPreferences", {}).get("unitsOfMeasurement", "")
        )
        if uoms := received_uoms:
            # Save user prefs in .storage file
            await save_user_prefs(self.hass, self.email, uoms)
        else:
            uoms = await get_user_prefs(self.hass, self.email)

        if uoms:
            uoms = uoms.split(" ")
            user_prefs = UserPreferenceUnits(
                distance=JLR_TO_HASS_UNITS.get(
                    uoms[0], self.hass.config.units.length_unit
                ),
                fuel=JLR_TO_HASS_UNITS.get(uoms[1], self.hass.config.units.volume_unit),
                temp=JLR_TO_HASS_UNITS.get(
                    uoms[2], self.hass.config.units.temperature_unit
                ),
                pressure=self.hass.config.units.pressure_unit
                if self.pressure_unit == "Default"
                else self.pressure_unit,
                energy_regenerated=JLR_TO_HASS_UNITS.get(
                    uoms[4], UnitOfEnergy.KILO_WATT_HOUR
                ),
                energy_consumed=JLR_TO_HASS_UNITS.get(uoms[5], "Unknown"),
            )
        else:
            user_prefs = UserPreferenceUnits(
                distance=self.hass.config.units.length_unit,
                fuel=self.hass.config.units.volume_unit,
                temp=self.hass.config.units.temperature_unit,
                pressure=self.hass.config.units.pressure_unit,
                energy_regenerated=UnitOfEnergy.KILO_WATT_HOUR,
                energy_consumed=UnitOfEnergy.KILO_WATT_HOUR,
            )

        self.user = UserData(
            first_name=user.get("firstName", "Unkown"),
            middle_name=user.get("middleName", "Unknown"),
            last_name=user.get("lastName", "Unknown"),
            user_preferences=user_prefs,
            user_prefs_from_account=received_uoms is not None,
        )

        _LOGGER.debug("User Data: %s", self.user)

    async def async_get_vehicles(self) -> None:
        """Get list of vehicles."""
        if len(self.connection.vehicles) > 0:
            for vehicle in self.connection.vehicles:
                _LOGGER.debug("Vehicle: %s", vehicle.vin)
                self.vehicles[vehicle.vin] = VehicleData(vin=vehicle.vin, api=vehicle)
        else:
            _LOGGER.debug("No vehicles found in this account")

    async def async_get_vehicle_attributes(self, vehicle: VehicleData) -> None:
        """Get vehicle attributes."""
        attributes = await vehicle.api.get_attributes()

        # Remove capabilities data
        del attributes["capabilities"]

        # Sort order - mainly for diagnostics download
        attributes = dict(sorted(attributes.items()))

        if attributes:
            _LOGGER.debug(
                "Retrieved attribute data for %s",
                field_mask(vehicle.vin, 3, 2),
            )
            _LOGGER.debug(attributes)
            vehicle.attributes = attributes
            vehicle.fuel = attributes.get("fuelType")
            vehicle.name = attributes.get("nickname")
            self.get_vehicle_engine_type(vehicle)

            # Set supported services

            vehicle.supported_services = [
                service.get("serviceType")
                for service in attributes["availableServices"]
                if service.get("vehicleCapable") and service.get("serviceEnabled")
            ]
            _LOGGER.debug("SERVINFO: %s ", vehicle.supported_services)

            # Add privacy mode, service mode and transport mode support
            vehicle.supported_services.extend(["PM", "SM", "TM"])

            # Add preconditioning On and Off
            if "ECC" in vehicle.supported_services:
                vehicle.supported_services.extend(["ECCON", "ECCOFF"])

        else:
            _LOGGER.debug(
                "Attribute data is empty for %s",
                field_mask(vehicle.vin, 3, 2),
            )

    async def async_get_vehicle_status(self, vehicle: VehicleData) -> None:
        """Get vehicle status."""
        status: VehicleStatus = await vehicle.api.get_status()
        if status:
            debug_log_status(status)
            self.identify_status_changes(vehicle, status)
            vehicle.status = status
            vehicle.last_updated = status.last_updated_time
            vehicle.last_status_update = datetime.now()
            await self.get_tracked_statuses(vehicle)
            _LOGGER.debug("TRACKED STATUS: %s", vehicle.tracked_status)
        else:
            _LOGGER.debug(
                "Status data is empty for %s",
                field_mask(vehicle.vin, 3, 2),
            )

        # Get climate temp preference
        # TODO: Check if different for EV
        try:
            vehicle.target_climate_temp = 21
            if vehicle.engine_type in [
                PowerTrainType.INTERNAL_COMBUSTION,
                PowerTrainType.PHEV,
            ]:
                climate_temp_data = await vehicle.api.get_rcc_target_value()
                _LOGGER.debug("CLIMATE TEMP: %s", climate_temp_data)
                temp = int(float(climate_temp_data.get("value", "42"))) / 2
                vehicle.target_climate_temp = temp
                _LOGGER.debug("CLIMATE TEMP: %s", temp)
        except (HTTPError, AttributeError):
            pass

    def identify_status_changes(self, vehicle: VehicleData, new_status: VehicleStatus):
        """Debug log changed status params."""
        if vehicle.status:
            # Core Status
            for status_class in ["core", "ev"]:
                if getattr(vehicle.status, status_class):
                    for key, value in getattr(vehicle.status, status_class).items():
                        if value != getattr(new_status, status_class)[key]:
                            _LOGGER.debug(
                                "%s - prev: %s, new: %s",
                                key,
                                value,
                                getattr(new_status, status_class)[key],
                            )

            # Alerts
            for alert in vehicle.status.alerts:
                if (
                    alert.last_updated
                    != [
                        new_alert
                        for new_alert in new_status.alerts
                        if alert.name == new_alert.name
                    ][0].last_updated
                ):
                    message = (
                        "NEW ACTIVE ALERT" if alert.active else "ALERT BECAME INACTIVE"
                    )

                    _LOGGER.debug(
                        "%s: %s",
                        message,
                        alert,
                    )

        _LOGGER.debug("Last updated: %s", new_status.last_updated_time)
        _LOGGER.debug(
            "Last updated status: %s", new_status.last_updated_time_vehicle_status
        )
        _LOGGER.debug(
            "Last updated alerts: %s\n", new_status.last_updated_time_vehicle_alert
        )

    async def get_tracked_statuses(self, vehicle: VehicleData) -> None:
        """Populate tracked status items in vehicle data."""

        # Climate (engine) status - available for engine types ICE and Hybrid
        if vehicle.engine_type in [
            PowerTrainType.INTERNAL_COMBUSTION,
            PowerTrainType.PHEV,
        ]:
            vehicle.tracked_status.climate_engine_active = get_value_match(
                vehicle.status.core, "VEHICLE_STATE_TYPE", "ENGINE_ON_REMOTE_START"
            )

        # Climate (electric) status - available for engine types Electric and Hybrid
        # EV_PRECONDITION_OPERATING_STATUS has 3 climate states: OFF, PRECLIM (heating) and STARTUP (starting)
        if vehicle.engine_type in [PowerTrainType.BEV, PowerTrainType.PHEV]:
            vehicle.tracked_status.climate_electric_active = not get_value_match(
                vehicle.status.ev, "EV_PRECONDITION_OPERATING_STATUS", "OFF"
            )

        # Guardian mode
        vehicle.tracked_status.guardian_mode_active = get_value_match(
            vehicle.guardian_mode, "status", "ACTIVE"
        )

        # Charging
        vehicle.tracked_status.is_charging = get_value_match(
            vehicle.status.ev, "EV_CHARGING_STATUS", "CHARGING"
        )

        # Privacy mode status
        vehicle.tracked_status.privacy_mode_enabled = not get_value_match(
            vehicle.status.core, "PRIVACY_SWITCH", "TRUE"
        )

        # Service mode
        vehicle.tracked_status.service_mode_enabled = get_is_date_active(
            vehicle.status.core, "SERVICE_MODE_STOP"
        )

        # Transport mode
        vehicle.tracked_status.transport_mode_enabled = get_is_date_active(
            vehicle.status.core, "TRANSPORT_MODE_STOP"
        )

        await self.tracked_status_actions(vehicle)

    async def tracked_status_actions(self, vehicle: VehicleData):
        """Perform actions for tracked statuses."""
        if (
            vehicle.tracked_status.climate_electric_active
            or vehicle.tracked_status.climate_engine_active
        ):
            # Schedule status update in 1 min if not already scheduled
            vehicle.short_interval_monitor = True
        else:
            vehicle.short_interval_monitor = False

    def get_vehicle_engine_type(self, vehicle: VehicleData) -> None:
        """Determine vehicle engine type."""
        _LOGGER.debug(
            "Vehicle fuel type is %s - %s",
            vehicle.attributes.get("fuelType", "Unknown"),
            vehicle.attributes.get("powerTrainType", "Unknown"),
        )

        self.vehicles[vehicle.vin].engine_type = PowerTrainType[
            vehicle.attributes.get("powerTrainType")
        ]

    async def async_get_vehicle_position(self, vehicle: VehicleData) -> None:
        """Get vehicle position data."""
        position = await vehicle.api.get_position()

        if position:
            vehicle.position = position
            _LOGGER.debug(
                "Received position data update for %s",
                vehicle.name,
            )
        else:
            vehicle.position = None
            _LOGGER.debug(
                "No position data received for %s",
                vehicle.name,
            )

    async def async_get_guardian_mode_status(self, vehicle: VehicleData) -> None:
        """Get guardian mode status."""
        if "GMCC" in vehicle.supported_services:
            try:
                vehicle.guardian_mode = await vehicle.api.get_guardian_mode_status()
            except (HTTPError, JLRException):
                # If not supported
                vehicle.guardian_mode = GuardianData(
                    capable=False, active=False, expiry="0"
                )

    async def async_get_vehicle_last_trip_data(self, vehicle: VehicleData) -> None:
        """Get vehicle trip data."""

        trips = await vehicle.api.get_trips(1)
        if trips and trips.get("trips"):
            vehicle.last_trip = trips.get("trips")[0]
            _LOGGER.debug(
                "Retieved trip data update for %s",
                vehicle.name,
            )
        else:
            vehicle.last_trip = None
            _LOGGER.debug(
                "No trip data received for %s",
                vehicle.name,
            )

    async def async_status_only_update(self, vehicle: VehicleData):
        """Update vehicle status only."""
        await self.async_get_vehicle_status(vehicle)
        self.hass.async_add_executor_job(self.async_update_listeners)

    async def async_update_data(self):
        """Update vehicle data."""
        try:
            # Get user prefs if not yet received
            if not self.user.user_prefs_from_account:
                await self.async_get_user_info()

            for _, vehicle in self.vehicles.items():
                if (not vehicle.last_status_update) or (
                    datetime.now() - vehicle.last_status_update
                ) >= timedelta(seconds=30):
                    await self.async_get_vehicle_position(vehicle)
                    await self.async_get_guardian_mode_status(vehicle)
                    await self.async_get_vehicle_status(vehicle)

                    if vehicle.status.core["PRIVACY_SWITCH"] == "FALSE":
                        await self.async_get_vehicle_last_trip_data(vehicle)
                    else:
                        vehicle.last_trip = None
                        _LOGGER.debug(
                            "Journey recording is disabled. Trip data not loaded for %s",
                            vehicle.name,
                        )

                    _LOGGER.info(
                        "JLR InControl update received for %s",
                        vehicle.name,
                    )
            return True
        except JLRException as ex:
            _LOGGER.debug("Unable to update data from JLRInControl servers. %s", ex)
            return False

    async def async_call_service(self, service):
        """Handle service call."""
        if JLR_SERVICES[service.service]:
            _LOGGER.debug("Service Call: %s", service.data)
            entity_device_ids = []
            vin_list = []

            # Log warning if deprecated service call
            if service.service in DEPRECATED_SERVICES:
                deprecated_service = DEPRECATED_SERVICES[service.service]
                _LOGGER.warning(
                    "%s service has been deprecated from v3.0.0. Please use the service %s with entity %s instead",
                    service.service,
                    deprecated_service.get("use_instead_service"),
                    deprecated_service.get("use_instead_entity"),
                )

            # Make list of config_entry_ids and vins

            area_ids = service.data.get("area_id", [])

            # If entity_ids, get device_ids for entity or areas
            if entity_ids := service.data.get("entity_id") or area_ids:
                entity_reg = er.async_get(self.hass)
                entities = er.async_entries_for_config_entry(
                    entity_reg, self.config_entry.entry_id
                )
                entity_device_ids = [
                    entity.device_id
                    for entity in entities
                    if entity.entity_id in entity_ids or entity.area_id in area_ids
                ]

            # Get device ids for this instance and areas
            if device_ids := service.data.get("entity_id") or area_ids:
                device_reg = dr.async_get(self.hass)
                devices = dr.async_entries_for_config_entry(
                    device_reg, self.config_entry.entry_id
                )
                vin_list = [
                    dict(device.identifiers).get(DOMAIN)
                    for device in devices
                    if device.id in device_ids
                    or device.id in entity_device_ids
                    or device.area_id in area_ids
                ]

            _LOGGER.debug("VIN list: %s", vin_list)

            if vin_list:
                # Remove duplicate device ids
                vin_list = list(set(vin_list))

                # Get service info
                kwargs = {}
                for key, value in service.data.items():
                    kwargs[key] = value

                # Call service on each unique device
                for vin in vin_list:
                    jlr_service = JLRService(self, vin, service.service)
                    success = await jlr_service.async_call_service(**kwargs)
                    if success:
                        _LOGGER.debug(
                            "Service call %s on vehicle %s successful. ",
                            service.service,
                            self.vehicles[vin].attributes.get("nickname"),
                        )
                # Call update on return of monitor
                await self.async_update_data()
