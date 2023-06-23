"""Support for JLR InControl Device Trackers."""
import logging

from homeassistant.components.device_tracker import SOURCE_TYPE_GPS
from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, JLR_DATA
from .entity import JLREntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Setup device tracker"""
    coordinator = hass.data[DOMAIN][config_entry.entry_id][JLR_DATA]
    devices = []

    for vehicle in coordinator.vehicles:
        if coordinator.vehicles[vehicle].position:
            devices.append(JLRDeviceTracker(coordinator, vehicle))

        else:
            _LOGGER.debug(
                "Vehicle %s is not providing any position information.",
                coordinator.vehicles[vehicle].attributes.get("nickname"),
            )

    async_add_entities(devices, True)


class JLRDeviceTracker(JLREntity, TrackerEntity):
    """Device tracker"""

    def __init__(self, coordinator: DataUpdateCoordinator, vin: str) -> None:
        super().__init__(coordinator, vin, "device tracker")
        self._position = None
        self._latitude = None
        self._longitude = None
        self._icon = "mdi:car-connected"

    async def async_update(self):
        """Update the device info."""
        _LOGGER.debug("Updating %s", self._name)
        try:
            self._position = self.vehicle.position.get("position")

            if self._position:
                self._latitude = round(self._position.get("latitude"), 8)
                self._longitude = round(self._position.get("longitude"), 8)
        except Exception as ex:
            _LOGGER.debug(
                "Unable to update device tracker for %s. Error is %s",
                self._name,
                ex,
            )

    @property
    def extra_state_attributes(self):
        attrs = {}

        try:
            loc_name = self.hass.async_add_exexutor_job(
                self.coordinator.connection.reverse_geocode,
                (self._latitude, self._longitude),
            )
            attrs["location"] = loc_name.get("formattedAddress")
        except Exception:
            pass
        attrs["speed"] = self._position.get("speed")
        attrs["heading"] = self._position.get("heading")

        return attrs

    @property
    def latitude(self) -> float:
        """Return latitude value of the device."""
        return self._latitude

    @property
    def longitude(self) -> float:
        """Return longitude value of the device."""
        return self._longitude

    @property
    def source_type(self):
        """Return the source type, eg gps or router, of the device."""
        return SOURCE_TYPE_GPS
