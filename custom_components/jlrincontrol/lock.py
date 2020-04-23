"""Support for JLR InControl Locks."""
import logging

# from homeassistant.const import STATE_OFF, UNIT_PERCENTAGE
from homeassistant.components.lock import LockDevice
from . import JLREntity, DOMAIN
from .services import JLRService
from .const import DATA_ATTRS_DOOR_POSITION, DATA_ATTRS_DOOR_STATUS


_LOGGER = logging.getLogger(__name__)
DATA_KEY = DOMAIN


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    data = hass.data[DOMAIN]
    if discovery_info is None:
        return

    _LOGGER.debug(
        "Setting Up Lock Sensors for - {}".format(
            data.vehicles[discovery_info].attributes.get("nickname")
        )
    )

    devices = []
    devices.append(JLRLock(hass, discovery_info))
    data.entities.extend(devices)
    async_add_entities(devices, True)


class JLRLock(JLREntity, LockDevice):
    def __init__(self, hass, vin, *args):
        self._icon = "mdi:car-key"
        self._sensor_name = "doors"
        super().__init__(hass, vin)

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
            jlr_service = JLRService(self._hass, self._vehicle)
            await jlr_service.async_call_service(**kwargs)
        else:
            _LOGGER.warning("Cannot lock vehicle - pin not set in configuration.yaml")

    async def async_unlock(self, **kwargs):
        """Unlock the car."""
        _LOGGER.debug("Unlocking vehicle")
        p = self._data.pin
        if p:
            kwargs = {}
            kwargs["service_name"] = "unlock"
            kwargs["service_code"] = "RDU"
            kwargs["pin"] = p
            jlr_service = JLRService(self._hass, self._vehicle)
            await jlr_service.async_call_service(**kwargs)
        else:
            _LOGGER.warning("Cannot unlock vehicle - pin not set in configuration.yaml")

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
