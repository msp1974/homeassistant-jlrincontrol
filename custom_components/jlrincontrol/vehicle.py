"""Class to handle JLR Vehicle."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
from urllib.error import HTTPError

from aiojlrpy import Connection, Vehicle, VehicleStatus
from aiojlrpy.exceptions import JLRException

from homeassistant.core import HomeAssistant

from .const import PowerTrainType
from .util import debug_log_status, field_mask, get_is_date_active, get_value_match

_LOGGER = logging.getLogger(__name__)


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
class JLRVehicle:
    """Class to hold vehicle data and functions."""

    vin: str
    hass: HomeAssistant
    connection: Connection
    api: Vehicle
    pin: str
    name: str = ""
    engine_type: str = "Unknown"
    fuel: str = "Unknown"
    last_updated: datetime = None
    last_status_update: datetime = None
    position: dict = field(default_factory=dict)
    address: dict = field(default_factory=dict)
    attributes: dict = field(default_factory=dict)
    supported_services: list = field(default_factory=list)
    status: VehicleStatus = field(default_factory=VehicleStatus)
    guardian_mode: dict = field(default_factory=dict)
    tracked_status: TrackedStatuses = field(default_factory=TrackedStatuses)
    last_trip: dict = field(default_factory=dict)
    trips: dict = field(default_factory=dict)
    target_climate_temp: int = 21
    short_interval_monitor: bool = False

    async def update_data(self) -> bool:
        """Update vehicle data from api."""
        if (not self.last_status_update) or (
            datetime.now() - self.last_status_update
        ) >= timedelta(seconds=30):
            await self.async_get_vehicle_position()
            await self.async_get_guardian_mode_status()
            await self.async_get_vehicle_status()

            if self.status.core["PRIVACY_SWITCH"] == "FALSE":
                await self.async_get_vehicle_last_trip_data()
            else:
                self.last_trip = None
                _LOGGER.debug(
                    "Journey recording is disabled. Trip data not loaded for %s",
                    self.name,
                )

            _LOGGER.info(
                "JLR InControl update received for %s",
                self.name,
            )

    async def async_get_vehicle_attributes(self) -> None:
        """Get vehicle attributes."""
        attributes = await self.api.get_attributes()

        # Remove capabilities data
        del attributes["capabilities"]

        # Sort order - mainly for diagnostics download
        attributes = dict(sorted(attributes.items()))

        if attributes:
            _LOGGER.debug(
                "Retrieved attribute data for %s",
                field_mask(self.vin, 3, 2),
            )
            _LOGGER.debug(attributes)
            self.attributes = attributes
            self.fuel = attributes.get("fuelType")
            self.name = attributes.get("nickname")
            self.get_vehicle_engine_type()

            # Set supported services

            self.supported_services = [
                service.get("serviceType")
                for service in attributes["availableServices"]
                if service.get("vehicleCapable") and service.get("serviceEnabled")
            ]
            _LOGGER.debug("SERVINFO: %s ", self.supported_services)

            # Add privacy mode, service mode and transport mode support
            self.supported_services.extend(["PM", "SM", "TM"])

            # Add preconditioning On and Off
            if "ECC" in self.supported_services:
                self.supported_services.extend(["ECCON", "ECCOFF"])

        else:
            _LOGGER.debug(
                "Attribute data is empty for %s",
                field_mask(self.vin, 3, 2),
            )

    async def async_get_vehicle_status(self) -> None:
        """Get vehicle status."""
        status: VehicleStatus = await self.api.get_status()
        if status:
            debug_log_status(status)
            self.identify_status_changes(status)
            self.status = status
            self.last_updated = status.last_updated_time
            self.last_status_update = datetime.now()
            await self.get_tracked_statuses()
            _LOGGER.debug("TRACKED STATUS: %s", self.tracked_status)
        else:
            _LOGGER.debug(
                "Status data is empty for %s",
                field_mask(self.vin, 3, 2),
            )

        # Get climate temp preference
        # TODO: Check if different for EV
        try:
            self.target_climate_temp = 21
            if self.engine_type in [
                PowerTrainType.INTERNAL_COMBUSTION,
                PowerTrainType.PHEV,
            ]:
                climate_temp_data = await self.api.get_rcc_target_value()
                _LOGGER.debug("CLIMATE TEMP: %s", climate_temp_data)
                temp = int(float(climate_temp_data.get("value", "42"))) / 2
                self.target_climate_temp = temp
                _LOGGER.debug("CLIMATE TEMP: %s", temp)
        except (HTTPError, AttributeError):
            pass

    def identify_status_changes(self, new_status: VehicleStatus):
        """Debug log changed status params."""
        if self.status:
            # Core Status
            for status_class in ["core", "ev"]:
                if getattr(self.status, status_class):
                    for key, value in getattr(self.status, status_class).items():
                        try:
                            if value != getattr(new_status, status_class)[key]:
                                _LOGGER.debug(
                                    "%s - prev: %s, new: %s",
                                    key,
                                    value,
                                    getattr(new_status, status_class)[key],
                                )
                        except KeyError:
                            _LOGGER.debug("Key %s no longer exists in updated status", key)

            # Alerts
            if self.status.alerts:
                for alert in new_status.alerts:
                    if (
                        alert.last_updated
                        != [
                            prev_alert
                            for prev_alert in self.status.alerts
                            if alert.name == prev_alert.name
                        ][0].last_updated
                    ):
                        message = (
                            "NEW ACTIVE ALERT"
                            if alert.active
                            else "ALERT BECAME INACTIVE"
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

    async def get_tracked_statuses(self) -> None:
        """Populate tracked status items in vehicle data."""

        # Climate (engine) status - available for engine types ICE and Hybrid
        if self.engine_type in [
            PowerTrainType.INTERNAL_COMBUSTION,
            PowerTrainType.PHEV,
        ]:
            self.tracked_status.climate_engine_active = get_value_match(
                self.status.core, "VEHICLE_STATE_TYPE", "ENGINE_ON_REMOTE_START"
            )

        # Climate (electric) status - available for engine types Electric and Hybrid
        # EV_PRECONDITION_OPERATING_STATUS has 3 climate states: OFF, PRECLIM (heating) and STARTUP (starting)
        if self.engine_type in [PowerTrainType.BEV, PowerTrainType.PHEV]:
            self.tracked_status.climate_electric_active = not get_value_match(
                self.status.ev, "EV_PRECONDITION_OPERATING_STATUS", "OFF"
            )

        # Guardian mode
        self.tracked_status.guardian_mode_active = get_value_match(
            self.guardian_mode, "status", "ACTIVE"
        )

        # Charging
        self.tracked_status.is_charging = get_value_match(
            self.status.ev, "EV_CHARGING_STATUS", "CHARGING"
        )

        # Privacy mode status
        self.tracked_status.privacy_mode_enabled = not get_value_match(
            self.status.core, "PRIVACY_SWITCH", "TRUE"
        )

        # Service mode
        self.tracked_status.service_mode_enabled = get_is_date_active(
            self.status.core, "SERVICE_MODE_STOP"
        )

        # Transport mode
        self.tracked_status.transport_mode_enabled = get_is_date_active(
            self.status.core, "TRANSPORT_MODE_STOP"
        )

        await self.tracked_status_actions()

    async def tracked_status_actions(self):
        """Perform actions for tracked statuses."""
        if (
            self.tracked_status.climate_electric_active
            or self.tracked_status.climate_engine_active
        ):
            # Schedule status update in 1 min if not already scheduled
            self.short_interval_monitor = True
        else:
            self.short_interval_monitor = False

    def get_vehicle_engine_type(self) -> None:
        """Determine vehicle engine type."""
        _LOGGER.debug(
            "Vehicle fuel type is %s - %s",
            self.attributes.get("fuelType", "Unknown"),
            self.attributes.get("powerTrainType", "Unknown"),
        )

        self.engine_type = PowerTrainType[self.attributes.get("powerTrainType")]

    async def async_get_vehicle_position(self) -> None:
        """Get vehicle position data."""
        last_position = self.position
        position = await self.api.get_position()

        if position:
            self.position = position.get("position")
            _LOGGER.debug(
                "Received position data update for %s",
                self.name,
            )

            # Get address only if new position to reduce api requests
            if self.position != last_position:
                _LOGGER.debug("Vehicle has new position, getting address data")

                # Get address details
                address = await self.connection.reverse_geocode(
                    round(self.position.get("latitude"), 8),
                    round(self.position.get("longitude"), 8),
                )
                if address:
                    self.address = address
                else:
                    self.address = {"formattedAddress": "Unknown"}
        else:
            self.position = None
            _LOGGER.debug(
                "No position data received for %s",
                self.name,
            )

    async def async_get_guardian_mode_status(self) -> None:
        """Get guardian mode status."""
        if "GMCC" in self.supported_services:
            try:
                self.guardian_mode = await self.api.get_guardian_mode_status()
            except (HTTPError, JLRException):
                # If not supported
                self.guardian_mode = GuardianData(
                    capable=False, active=False, expiry="0"
                )

    async def async_get_vehicle_last_trip_data(self) -> None:
        """Get vehicle trip data."""

        trips = await self.api.get_trips(1)
        if trips and trips.get("trips"):
            self.last_trip = trips.get("trips")[0]
            _LOGGER.debug(
                "Retieved trip data update for %s",
                self.name,
            )
        else:
            self.last_trip = None
            _LOGGER.debug(
                "No trip data received for %s",
                self.name,
            )
