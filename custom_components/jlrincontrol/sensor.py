"""Support for JLR InControl Sensors."""
import logging

# from homeassistant.const import STATE_OFF, UNIT_PERCENTAGE
from . import JLREntity, DOMAIN
from homeassistant.const import UNIT_PERCENTAGE
from .const import (
    DATA_ATTRS_CAR_INFO,
    DATA_ATTRS_TYRE_STATUS,
    DATA_ATTRS_TYRE_PRESSURE,
    DATA_ATTRS_DOOR_STATUS,
    DATA_ATTRS_DOOR_POSITION,
    DATA_ATTRS_WINDOW_STATUS,
    DATA_ATTRS_SERVICE_STATUS,
    SERVICE_STATUS_OK,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    data = hass.data[DOMAIN]
    devices = []
    _LOGGER.debug("Loading sensors")

    devices.append(JLRVehicleSensor(data))
    devices.append(JLRVehicleWindowSensor(data))
    devices.append(JLRVehicleTyreSensor(data))
    devices.append(JLRVehicleServiceSensor(data))
    devices.append(JLRVehicleRangeSensor(data))

    async_add_entities(devices, True)


class JLRVehicleSensor(JLREntity):
    def __init__(self, data):
        super().__init__(data, "vehicle")
        _LOGGER.debug(
            "Loading vehicles sensors for {}".format(
                self._data.attributes.get("registrationNumber")
            )
        )
        self._icon = "mdi:car"
        self._name = self._data.attributes.get("nickname") + " Info"

    @property
    def state(self):
        x = self._data.attributes.get("registrationNumber")
        _LOGGER.debug("Reg - {}".format(x))
        return x

    @property
    def device_state_attributes(self):
        a = self._data.attributes
        attrs = {}

        for k, v in DATA_ATTRS_CAR_INFO.items():
            attrs[k.title()] = a.get(v)

        attrs["Odometer"] = self._data.get_odometer()
        attrs["State"] = self._data.wakeup.get("state").title()
        attrs["Next Update"] = self._data.wakeup.get("wakeupTime")
        return attrs


class JLRVehicleTyreSensor(JLREntity):
    def __init__(self, data):
        super().__init__(data, "tyre")
        _LOGGER.debug(
            "Loading tyre sensors for {}".format(
                self._data.attributes.get("registrationNumber")
            )
        )
        self._icon = "mdi:car-tire-alert"
        self._name = self._data.attributes.get("nickname") + " Tyres"

    @property
    def state(self):
        # Convert to list of values from dict
        if all(
            [
                self._data.status.get(v) == "NORMAL"
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

        s = self._data.status
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
        super().__init__(data, "window")
        _LOGGER.debug(
            "Loading vehicle status sensors for {}".format(
                self._data.attributes.get("registrationNumber")
            )
        )
        self._icon = "mdi:car-door"
        self._name = self._data.attributes.get("nickname") + " Windows"

    @property
    def state(self):
        if all(
            [
                self._data.status.get(v) == "CLOSED"
                for k, v in DATA_ATTRS_WINDOW_STATUS.items()
            ]
        ):
            return "Closed"
        else:
            return "Open"

    @property
    def device_state_attributes(self):
        s = self._data.status
        attrs = {}
        for k, v in DATA_ATTRS_WINDOW_STATUS.items():
            attrs[k.title() + " Position"] = s.get(v).title()

        return attrs


class JLRVehicleServiceSensor(JLREntity):
    def __init__(self, data):
        super().__init__(data, "service_info")
        _LOGGER.debug(
            "Loading vehicle status sensors for {}".format(
                self._data.attributes.get("registrationNumber")
            )
        )
        self._icon = "mdi:wrench"
        self._name = self._data.attributes.get("nickname") + " Service Info"

    @property
    def state(self):
        if all(
            [
                self._data.status.get(v) in SERVICE_STATUS_OK
                for k, v in DATA_ATTRS_SERVICE_STATUS.items()
            ]
        ):
            return "Ok"
        else:
            return "Warning"

    @property
    def device_state_attributes(self):
        s = self._data.status
        attrs = {}
        for k, v in DATA_ATTRS_SERVICE_STATUS.items():
            attrs[k.title()] = s.get(v).title()

        return attrs


class JLRVehicleRangeSensor(JLREntity):
    def __init__(self, data):
        super().__init__(data, "range")
        _LOGGER.debug(
            "Loading vehicle range sensors for {}".format(
                self._data.attributes.get("registrationNumber")
            )
        )
        self._icon = "mdi:gas-station"
        self._name = self._data.attributes.get("nickname") + " Range"

    @property
    def state(self):
        return self._data.dist_to_user_prefs(
            self._data.status.get("DISTANCE_TO_EMPTY_FUEL")
        )

    @property
    def device_state_attributes(self):
        # TODO: If fuelTankVolume is not none show remaining litres
        attrs = {}
        attrs["Fuel Type"] = self._data.attributes.get("fuelType")
        attrs["Fuel Level"] = self._data.status.get("FUEL_LEVEL_PERC") + UNIT_PERCENTAGE

        return attrs
