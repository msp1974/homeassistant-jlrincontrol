"""Support for JLR InControl Sensors."""
import logging

# from homeassistant.const import STATE_OFF, UNIT_PERCENTAGE
from . import JLREntity, DOMAIN
from .const import (
    DATA_ATTRS_CAR_INFO,
    DATA_ATTRS_TYRE_STATUS,
    DATA_ATTRS_TYRE_PRESSURE,
    DATA_ATTRS_DOOR_STATUS,
    DATA_ATTRS_DOOR_POSITION,
    DATA_ATTRS_WINDOW_STATUS,
    DATA_ATTRS_SERVICE_STATUS,
)

_LOGGER = logging.getLogger(__name__)
DATA_KEY = DOMAIN


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    data = hass.data[DOMAIN]
    devices = []
    _LOGGER.debug("Loading sensors")

    devices.append(JLRVehicleSensor(data))
    devices.append(JLRVehicleWindowSensor(data))
    devices.append(JLRVehicleTyreSensor(data))
    devices.append(JLRVehicleServiceSensor(data))

    async_add_entities(devices, True)


class JLRVehicleSensor(JLREntity):
    def __init__(self, data):
        super().__init__(data, "vehicle")
        self.data = data
        _LOGGER.debug(
            "Loading vehicles sensors for {}".format(
                self.data.attributes.get("registrationNumber")
            )
        )
        self._icon = "mdi:car"
        self._name = self.data.attributes.get("nickname") + " Info"

    @property
    def state(self):
        x = self.data.attributes.get("registrationNumber")
        _LOGGER.debug("Reg - {}".format(x))
        return x

    @property
    def device_state_attributes(self):
        a = self.data.attributes
        p = self.data.position
        attrs = {}

        for k, v in DATA_ATTRS_CAR_INFO.items():
            attrs[k.title()] = a.get(v)

        attrs["Odometer"] = self.data.get_odometer()
        attrs["Latitude"] = round(p.get("position").get("latitude"), 8)
        attrs["Longitude"] = round(p.get("position").get("longitude"), 8)
        return attrs


class JLRVehicleTyreSensor(JLREntity):
    def __init__(self, data):
        super().__init__(data, "tyre")
        self.data = data
        _LOGGER.debug(
            "Loading tyre sensors for {}".format(
                self.data.attributes.get("registrationNumber")
            )
        )
        self._icon = "mdi:car-tire-alert"
        self._name = self.data.attributes.get("nickname") + " Tyres"

    @property
    def state(self):
        # Convert to list of values from dict
        if all(
            [
                self.data.status.get(v) == "NORMAL"
                for k, v in DATA_ATTRS_TYRE_STATUS.items()
            ]
        ):
            return "Ok"
        else:
            return "Warning"

    @property
    def device_state_attributes(self):
        def __toPSI(bar):
            return round((int(bar) / 100) * 14.5038, 1)

        s = self.data.status
        attrs = {}

        # Statuses
        for k, v in DATA_ATTRS_TYRE_STATUS.items():
            attrs[k.title() + " Status"] = s.get(v).title()
        # Pressures
        for k, v in DATA_ATTRS_TYRE_PRESSURE.items():
            attrs[k.title() + " Pressure (PSI)"] = __toPSI(s.get(v))

        return attrs


class JLRVehicleWindowSensor(JLREntity):
    def __init__(self, data):
        super().__init__(data, "vehicle")
        self.data = data
        _LOGGER.debug(
            "Loading vehicle status sensors for {}".format(
                self.data.attributes.get("registrationNumber")
            )
        )
        self._icon = "mdi:car-door"
        self._name = self.data.attributes.get("nickname") + " Windows"

    @property
    def state(self):
        if all(
            [
                self.data.status.get(v) == "CLOSED"
                for k, v in DATA_ATTRS_WINDOW_STATUS.items()
            ]
        ):
            return "Ok"
        else:
            return "Warning"

    @property
    def device_state_attributes(self):
        s = self.data.status
        attrs = {}
        for k, v in DATA_ATTRS_WINDOW_STATUS.items():
            attrs[k.title() + " Status"] = s.get(v).title()

        return attrs


class JLRVehicleServiceSensor(JLREntity):
    def __init__(self, data):
        super().__init__(data, "vehicle")
        self.data = data
        _LOGGER.debug(
            "Loading vehicle status sensors for {}".format(
                self.data.attributes.get("registrationNumber")
            )
        )
        self._icon = "mdi:wrench"
        self._name = self.data.attributes.get("nickname") + " Service Info"

    @property
    def state(self):
        if all(
            [
                self.data.status.get(v) == "NORMAL"
                for k, v in DATA_ATTRS_SERVICE_STATUS.items()
            ]
        ):
            return "Ok"
        else:
            return "Warning"

    @property
    def device_state_attributes(self):
        s = self.data.status
        attrs = {}
        for k, v in DATA_ATTRS_SERVICE_STATUS.items():
            attrs[k.title() + " Status"] = s.get(v).title()

        return attrs
