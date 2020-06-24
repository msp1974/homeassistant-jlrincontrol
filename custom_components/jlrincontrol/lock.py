"""Support for JLR InControl Locks."""
import logging

# from homeassistant.const import STATE_OFF, UNIT_PERCENTAGE
from homeassistant.components.lock import LockEntity
from .services import JLRService
from .const import (
    DOMAIN,
    DATA_ATTRS_DOOR_POSITION,
    DATA_ATTRS_DOOR_STATUS,
    JLR_DATA,
)
from .entity import JLREntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    data = hass.data[DOMAIN][config_entry.entry_id][JLR_DATA]
    devices = []

    for vehicle in data.vehicles:
        devices.append(JLRLock(hass, data, vehicle))
        data.entities.extend(devices)
        async_add_entities(devices, True)


class JLRLock(JLREntity, LockEntity):
    def __init__(self, hass, data, vin):
        self._icon = "mdi:car-key"
        self._sensor_name = "doors"
        super().__init__(hass, data, vin)

    @property
    def is_locked(self):
        """Return true if lock is locked."""
        return self._vehicle.status.get("DOOR_IS_ALL_DOORS_LOCKED") == "TRUE"

    async def async_lock(self, **kwargs):
        """Lock the car."""
        _LOGGER.debug("Locking vehicle")
        p = self._data.pin
        if p:
            kwargs = {}
            kwargs["service_name"] = "lock"
            kwargs["service_code"] = "RDL"
            kwargs["pin"] = p
            jlr_service = JLRService(
                self._hass, self._data.config_entry, self._vin
            )
            await jlr_service.async_call_service(**kwargs)
            await self._data.async_update()
        else:
            _LOGGER.warning("Cannot lock vehicle - pin not set in options.")

    async def async_unlock(self, **kwargs):
        """Unlock the car."""
        _LOGGER.debug("Unlocking vehicle")
        p = self._data.pin
        if p:
            kwargs = {}
            kwargs["service_name"] = "unlock"
            kwargs["service_code"] = "RDU"
            kwargs["pin"] = p
            jlr_service = JLRService(
                self._hass, self._data.config_entry, self._vin
            )
            await jlr_service.async_call_service(**kwargs)
            await self._data.async_update()
        else:
            _LOGGER.warning("Cannot unlock vehicle - pin not set in options.")

    @property
    def device_state_attributes(self):
        s = self._vehicle.status
        attrs = {}
        for k, v in DATA_ATTRS_DOOR_STATUS.items():
            if s.get(v) and s.get(v) != "UNKNOWN":
                attrs[k.title() + " Status"] = s.get(v).title()

        for k, v in DATA_ATTRS_DOOR_POSITION.items():
            if s.get(v) and s.get(v) != "UNKNOWN":
                attrs[k.title() + " Position"] = s.get(v).title()

        return attrs
