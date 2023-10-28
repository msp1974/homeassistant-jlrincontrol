"""Base entity"""

import asyncio
import logging

from homeassistant.core import callback
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class JLREntity(CoordinatorEntity, Entity):
    """Base entity class"""

    def __init__(self, coordinator: DataUpdateCoordinator, vin: str, name: str) -> None:
        """Create a new generic JLR sensor."""
        super().__init__(coordinator)
        self.hass = coordinator.hass
        self.vin = vin
        self._name = name
        self._icon = "mdi:cloud"

        self.vehicle = self.coordinator.vehicles[self.vin]

        _LOGGER.debug("Loading %s", self.name)

    @property
    def _entity_prefix(self):
        return (
            self.vehicle.attributes.get("vehicleBrand")
            + self.vehicle.attributes.get("vehicleType")
            + "-"
            + self.vin[-6:]
        )

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self.vin)}}

    @property
    def icon(self):
        return self._icon

    @property
    def name(self):
        return f"{self.vehicle.attributes.get('nickname')} {self._name.title()}"

    @property
    def unique_id(self):
        return f"{self._entity_prefix}-{self._name}"

    @property
    def extra_state_attributes(self):
        attrs = {}
        return attrs

    async def async_force_update(self, delay: int = 0):
        """Force update"""
        _LOGGER.debug("Update initiated by %s", self.name)
        if delay:
            await asyncio.sleep(delay)
        await self.coordinator.async_request_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        _LOGGER.debug("%s update request", self.name)
        self.async_write_ha_state()
