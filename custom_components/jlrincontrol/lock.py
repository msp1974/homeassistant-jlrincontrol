"""Support for JLR InControl Locks."""

import logging

from homeassistant.components.lock import LockEntity
from homeassistant.core import HomeAssistant

from .const import DATA_ATTRS_DOOR_POSITION, DATA_ATTRS_DOOR_STATUS, DOMAIN, JLR_DATA
from .entity import JLREntity
from .services import JLRService

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Initialise lock entities."""

    coordinator = hass.data[DOMAIN][config_entry.entry_id][JLR_DATA]
    devices = []

    for vehicle in coordinator.vehicles:
        devices.append(JLRLock(coordinator, vehicle))
        coordinator.entities.extend(devices)
        async_add_entities(devices, True)


class JLRLock(JLREntity, LockEntity):
    """Handles lock entity."""

    def __init__(self, coordinator, vin) -> None:
        """Initialise."""
        super().__init__(coordinator, vin, "doors")
        self._icon = "mdi:car-key"

    @property
    def is_locked(self):
        """Return true if lock is locked."""
        return self.vehicle.status.core["DOOR_IS_ALL_DOORS_LOCKED"] == "TRUE"

    async def async_lock(self, **kwargs):
        """Lock the car."""
        _LOGGER.debug("Locking vehicle")

        if self.vehicle.pin:
            kwargs = {}
            kwargs["service_name"] = "lock"
            kwargs["service_code"] = "RDL"
            kwargs["pin"] = self.vehicle.pin
            jlr_service = JLRService(self.coordinator, self.vin, "lock_vehicle")
            await jlr_service.async_call_service(**kwargs)
            await self.async_force_update()
        else:
            _LOGGER.warning("Cannot lock vehicle - pin not set in options")

    async def async_unlock(self, **kwargs):
        """Unlock the car."""
        _LOGGER.debug("Unlocking vehicle")

        if self.vehicle.pin:
            kwargs = {}
            kwargs["service_name"] = "unlock"
            kwargs["service_code"] = "RDU"
            kwargs["pin"] = self.vehicle.pin
            jlr_service = JLRService(self.coordinator, self.vin, "unlock_vehicle")
            await jlr_service.async_call_service(**kwargs)
            await self.async_force_update()
        else:
            _LOGGER.warning("Cannot unlock vehicle - pin not set in options")

    @property
    def extra_state_attributes(self):
        """Return attributes."""
        status = self.vehicle.status
        attrs = {}
        for key, value in DATA_ATTRS_DOOR_STATUS.items():
            if status.core.get(value) and status.core.get(value) != "UNKNOWN":
                attrs[key.title() + " Status"] = status.core.get(value).title()

        for key, value in DATA_ATTRS_DOOR_POSITION.items():
            if status.core.get(value) and status.core.get(value) != "UNKNOWN":
                attrs[key.title() + " Position"] = status.core.get(value).title()

        return attrs
