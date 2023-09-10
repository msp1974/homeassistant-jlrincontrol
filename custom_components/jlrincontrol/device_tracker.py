"""Support for JLR InControl Device Trackers."""
import logging
from urllib.error import HTTPError

from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, JLR_DATA
from .entity import JLREntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Setup device tracker"""
    coordinator = hass.data[DOMAIN][config_entry.entry_id][JLR_DATA]
    devices = []

    for vehicle in coordinator.vehicles:
        if coordinator.vehicles[vehicle].position:
            devices.append(JLRDeviceTracker(coordinator, vehicle))

        else:
            _LOGGER.debug(
                "Vehicle %s is not providing any position information",
                coordinator.vehicles[vehicle].attributes.get("nickname"),
            )

    async_add_entities(devices, True)


class JLRDeviceTracker(JLREntity, TrackerEntity):
    """Device tracker"""

    def __init__(self, coordinator: DataUpdateCoordinator, vin: str) -> None:
        super().__init__(coordinator, vin, "device tracker")
        self._position = None
        self._last_position = None
        self._address = None
        self._icon = "mdi:car-connected"

    def has_position_changed(self) -> bool:
        """Have geocode position changed"""
        if self._last_position:
            old_lat = round(self._last_position.get("latitude"), 8)
            new_lat = round(self._position.get("latitude"), 8)

            old_lon = round(self._last_position.get("longitude"), 8)
            new_lon = round(self._position.get("longitude"), 8)

            if (old_lat != new_lat) or (old_lon != new_lon):
                return True
            else:
                return False
        return True

    async def async_update(self):
        """Update the device info."""
        _LOGGER.debug("Updating %s", self._name)
        self._last_position = self._position
        self._position = self.vehicle.position.get("position", {})

        # Only call geocode if position has changed
        if self.has_position_changed():
            try:
                self._address = await self.hass.async_add_executor_job(
                    self.coordinator.connection.reverse_geocode,
                    round(self._position.get("latitude"), 8),
                    round(self._position.get("longitude"), 8),
                )
            except HTTPError:
                self._address = {"formattedAddress": "Unknown"}

    @property
    def extra_state_attributes(self):
        attrs = {}
        attrs["location"] = self._address.get("formattedAddress")
        attrs["speed"] = self._position.get("speed")
        attrs["heading"] = self._position.get("heading")

        return attrs

    @property
    def latitude(self) -> float:
        """Return latitude value of the device."""
        return round(self._position.get("latitude"), 8)

    @property
    def longitude(self) -> float:
        """Return longitude value of the device."""
        return round(self._position.get("longitude"), 8)

    @property
    def source_type(self):
        """Return the source type, eg gps or router, of the device."""
        return SourceType.GPS
