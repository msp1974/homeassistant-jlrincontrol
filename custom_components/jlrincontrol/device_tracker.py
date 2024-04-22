"""Support for JLR InControl Device Trackers."""

import logging

from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, JLR_DATA
from .entity import JLREntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Initialise device tracker."""
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
    """Device tracker."""

    def __init__(self, coordinator: DataUpdateCoordinator, vin: str) -> None:
        """Initialise."""
        super().__init__(coordinator, vin, "device tracker")
        self._icon = "mdi:car-connected"

    @property
    def extra_state_attributes(self):
        """Return sensor attributes."""
        attrs = {}
        attrs["location"] = self.vehicle.address.get("formattedAddress")
        attrs["speed"] = self.vehicle.position.get("speed")
        attrs["heading"] = self.vehicle.position.get("heading")

        return attrs

    @property
    def latitude(self) -> float:
        """Return latitude value of the device."""
        return round(self.vehicle.position.get("latitude"), 8)

    @property
    def longitude(self) -> float:
        """Return longitude value of the device."""
        return round(self.vehicle.position.get("longitude"), 8)

    @property
    def source_type(self):
        """Return the source type, eg gps or router, of the device."""
        return SourceType.GPS
