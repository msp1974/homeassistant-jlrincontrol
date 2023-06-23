import logging

from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from homeassistant.helpers.entity import Entity

from homeassistant.core import callback
from .const import DOMAIN
from jlrpy import Vehicle

_LOGGER = logging.getLogger(__name__)


class JLREntity(CoordinatorEntity, Entity):
    """Base entity class"""

    def __init__(
        self, coordinator: DataUpdateCoordinator, vin: str, name: str
    ):
        """Create a new generic JLR sensor."""
        super().__init__(coordinator)
        self.vin = vin
        self._name = name
        self._icon = "mdi:cloud"

        self.vehicle = self.coordinator.vehicles[self.vin]

        _LOGGER.debug("Loading %s Sensor", self.name)

    @property
    def _entity_prefix(self):
        return (
            self.vehicle.attributes.get("vehicleBrand")
            + self.vehicle.attributes.get("vehicleType")
            + "-"
            + self.vin[-6:]
        )

    @property
    def api(self):
        """Return api for vehicle"""
        try:
            return [
                vehicle
                for vehicle in self.coordinator.connection.vehicles
                if vehicle.vin == self.vin
            ][0]
        except IndexError:
            return None

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self.vin)}}

    @property
    def name(self):
        return (
            self.vehicle.attributes.get("nickname") + " " + self._name.title()
        )

    @property
    def unique_id(self):
        return f"{self._entity_prefix}-{self.name}"

    @property
    def assumed_state(self):
        """Return true if unable to access real state of entity."""
        return True

    def get_vehicle_api(self, vin: str) -> Vehicle | None:
        """Get jlrpy vehicle object"""
        try:
            return [
                vehicle
                for vehicle in self.coordinator.connection.vehicles
                if vehicle.vin == vin
            ][0]
        except IndexError:
            return None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        _LOGGER.debug("%s update request", self.name)
        self.async_write_ha_state()
