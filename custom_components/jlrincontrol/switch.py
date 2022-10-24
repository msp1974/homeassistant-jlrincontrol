"""Support for JLR InControl Switches"""
import logging

from homeassistant.components.switch import SwitchEntity, DEVICE_CLASS_SWITCH
from homeassistant.const import (
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    ATTR_ASSUMED_STATE,
)
from .services import JLRService
from .const import (
    DOMAIN,
    JLR_DATA,
    DATA_ATTRS_DOOR_POSITION,
    DATA_ATTRS_DOOR_STATUS,
    JLR_SERVICES,
    TEMP_CELSIUS,
    TEMP_FAHRENHEIT,
)

from .entity import JLREntity
from .util import convert_from_target_value

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    data = hass.data[DOMAIN][config_entry.entry_id][JLR_DATA]
    devices = []
    for vehicle in data.vehicles:
        for s in data.vehicles[vehicle].attributes.get("availableServices"):
            if s["serviceType"] == "REON" and s["vehicleCapable"]:
                devices.append(JLRRemoteStart(hass, data, vehicle))
                data.entities.extend(devices)
                async_add_entities(devices, True)


class JLRRemoteStart(JLREntity, SwitchEntity):
    def __init__(self, hass, data, vin):
        self._icon = "mdi:thermometer"
        self._sensor_name = "climate"
        self._vehicle_state = None
        self._remaining_run_time = None
        super().__init__(hass, data, vin)
        self._temp_unit = self._hass.config.units.temperature_unit

    @property
    def is_on(self):
        """Return true if car is remote started."""
        if self._state == "On":
            return True

    async def async_turn_on(self):
        """Start Remote Climate."""
        p = self._data.pin
        if p:
            if self._vehicle.status.get("DOOR_IS_ALL_DOORS_LOCKED") != "TRUE":
                _LOGGER.warning("Locking Vehicle Before attempting to start climate.")
                kwargs = {}
                kwargs["service_name"] = "lock"
                kwargs["service_code"] = "RDL"
                kwargs["pin"] = p
                jlr_service = JLRService(self._hass, self._data.config_entry, self._vin)
                await jlr_service.async_call_service(**kwargs)
            _LOGGER.debug("Starting Remote Climate")
            kwargs = {}
            kwargs["service_name"] = "remote_engine_start"
            kwargs["service_code"] = "REON"
            kwargs["pin"] = p
            kwargs["target_value"] = int(self._rcc_target_value)
            jlr_service = JLRService(self._hass, self._data.config_entry, self._vin)
            await jlr_service.async_call_service(**kwargs)
        else:
            _LOGGER.warning("Cannot start remote climate - pin not set in options.")

    async def async_turn_off(self):
        """Stopping Remote Climate."""
        _LOGGER.debug("Stopping Remote Climate")
        p = self._data.pin
        if p:
            kwargs = {}
            kwargs["service_name"] = "remote_engine_stop"
            kwargs["service_code"] = "REOFF"
            kwargs["pin"] = p
            jlr_service = JLRService(self._hass, self._data.config_entry, self._vin)
            await jlr_service.async_call_service(**kwargs)
        else:
            _LOGGER.warning("Cannot stop remote climate - pin not set in options.")

    @property
    def device_state_attributes(self):
        attrs = {}
        if self._vehicle_state == "ENGINE_ON_REMOTE_START":
            attrs["Remote Climate"] = "Running"
        else:
            attrs["Remote Climate"] = "Off"
        attrs["Remaining Run Time"] = "{}min".format(self._remaining_run_time)
        attrs["Climate Target Temp"] = convert_from_target_value(
            self._temp_unit, "REON", self._rcc_target_value
        )
        return attrs

    async def async_update(self):
        """Update the state of the switch."""
        await super().async_update()
        self._vehicle.get_rcc_target_value()["value"]
        self._remaining_run_time = self._vehicle.status.get(
            "CLIMATE_STATUS_REMAINING_RUNTIME"
        )
        self._vehicle_state = self._vehicle.status.get("VEHICLE_STATE_TYPE")
        self._rcc_target_value = int(self._vehicle.get_rcc_target_value()["value"])
        if self._vehicle_state == "ENGINE_ON_REMOTE_START":
            self._state = "On"
        else:
            self._state = "Off"
