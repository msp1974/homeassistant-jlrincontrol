"""Handles updating data from jlrpy."""

import asyncio
from datetime import timedelta
import json
import logging
from urllib.error import HTTPError

from aiojlrpy import Connection, JLRServices, StatusMessage, process_vhs_message
from aiojlrpy.exceptions import JLRException

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_PIN,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant
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
    VERSION,
)
from .services import JLRService
from .user import JLRUser
from .util import debug_log_status
from .vehicle import JLRVehicle

_LOGGER = logging.getLogger(__name__)


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
        self.user: JLRUser
        self.email = config_entry.data.get(CONF_USERNAME)
        self.password = config_entry.data.get(CONF_PASSWORD)
        self.use_china_servers = config_entry.data.get(CONF_USE_CHINA_SERVERS)
        self.device_id = config_entry.data.get(CONF_DEVICE_ID)
        self.vehicles: dict[str, JLRVehicle] = {}
        self.entities = []
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

            self.user = JLRUser(self.hass, self.config_entry, self.email)
            await self.user.async_get_user_info(self.connection)

            await self.async_get_vehicles()

            _LOGGER.debug("Connected to API")

            for vehicle in self.vehicles.values():
                await vehicle.async_get_vehicle_attributes()

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

    async def async_get_vehicles(self) -> None:
        """Get list of vehicles."""
        if len(self.connection.vehicles) > 0:
            for vehicle in self.connection.vehicles:
                _LOGGER.debug("Vehicle: %s", vehicle.vin)
                self.vehicles[vehicle.vin] = JLRVehicle(
                    vin=vehicle.vin,
                    hass=self.hass,
                    connection=self.connection,
                    api=vehicle,
                    pin=self.config_entry.data[CONF_PIN].get(vehicle.vin, "0000")
                    if isinstance(self.config_entry.data[CONF_PIN], dict)
                    else self.config_entry.data[CONF_PIN],
                )
        else:
            _LOGGER.debug("No vehicles found in this account")

    async def _on_ws_message(self, message: StatusMessage):
        """Websocket message callback function."""
        _LOGGER.debug(message)
        if self.vehicles:
            if message.service == JLRServices.GUARDIAN_MODE:
                if message.vin:
                    data = json.loads(message.data.get("b"))
                    self.vehicles[message.vin].guardian_mode = data
                    self.vehicles[message.vin].tracked_status.guardian_mode_active = (
                        data["status"] == "ACTIVE"
                    )
                    self.hass.async_add_executor_job(self.async_update_listeners)
            elif message.service == JLRServices.VEHICLE_HEALTH:
                if message.vin:
                    if data := message.data.get("b"):
                        json_data = json.loads(message.data.get("b"))
                        status = process_vhs_message(json_data)
                        debug_log_status(status)
                        self.vehicles[message.vin].identify_status_changes(status)
                        self.vehicles[message.vin].status = status
                        await self.vehicles[message.vin].get_tracked_statuses()
                        # Just had VHS message so cancel any outstanding status updates

                        if (
                            self.scheduled_update_task
                            and not self.scheduled_update_task.done()
                        ):
                            _LOGGER.debug(
                                "Cancelling scheduled status update as VHS message received in time"
                            )
                            self.scheduled_update_task.cancel()

                        self.hass.async_add_executor_job(self.async_update_listeners)

            elif (
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
                if (
                    not self.scheduled_update_task
                ) or self.scheduled_update_task.done():
                    _LOGGER.debug(
                        "Scheduling status update in 15s if VHS message not sent"
                    )
                    self.scheduled_update_task = asyncio.create_task(
                        self.get_delayed_vehicle_status(self.vehicles[message.vin], 15)
                    )

    async def get_delayed_vehicle_status(self, vehicle: JLRVehicle, delay: int = 0):
        """Get vehicle status."""
        await asyncio.sleep(delay)
        _LOGGER.debug("Calling update data caused by message with no VHS\n")
        await self.async_refresh()

    async def monitored_vehicle_status(self, interval: int):
        """Get vehicle status."""
        while True:
            await asyncio.sleep(interval)
            for vehicle in self.vehicles.values():
                if vehicle.short_interval_monitor:
                    _LOGGER.debug(
                        "Calling monitoring update status for %s", vehicle.name
                    )
                    await self.async_status_only_update(vehicle)

    async def async_status_only_update(self, vehicle: JLRVehicle):
        """Update vehicle status only."""
        await vehicle.async_get_vehicle_status()
        self.hass.async_add_executor_job(self.async_update_listeners)

    async def async_update_data(self):
        """Update vehicle data."""
        try:
            # Get user prefs if not yet received
            if not self.user.units_from_account:
                await self.user.async_get_user_info()

            for vehicle in self.vehicles.values():
                await vehicle.update_data()
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
