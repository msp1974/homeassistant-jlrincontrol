"""Support for JLR InControl Sensors."""
import logging

# from homeassistant.const import STATE_OFF, UNIT_PERCENTAGE
from . import JLREntity, DOMAIN
from homeassistant.const import UNIT_PERCENTAGE, LENGTH_KILOMETERS, LENGTH_MILES
from .const import (
    DATA_ATTRS_CAR_INFO,
    DATA_ATTRS_EV_CHARGE_INFO,
    DATA_ATTRS_TYRE_STATUS,
    DATA_ATTRS_TYRE_PRESSURE,
    DATA_ATTRS_DOOR_STATUS,
    DATA_ATTRS_DOOR_POSITION,
    DATA_ATTRS_WINDOW_STATUS,
    DATA_ATTRS_SERVICE_STATUS,
    DATA_ATTRS_SERVICE_INFO,
    FUEL_TYPE_BATTERY,
    SERVICE_STATUS_OK,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    data = hass.data[DOMAIN]
    devices = []
    _LOGGER.debug("Loading Sensors")

    devices.append(JLRVehicleSensor(data))
    devices.append(JLRVehicleWindowSensor(data))
    devices.append(JLRVehicleTyreSensor(data))
    devices.append(JLRVehicleServiceSensor(data))
    devices.append(JLRVehicleRangeSensor(data))

    # If EV show EV sensorl otherwise show fuel sensor
    if data.attributes.get("fuelType") == FUEL_TYPE_BATTERY:
        devices.append(JLREVChargeSensor(data))

    async_add_entities(devices, True)


class JLRVehicleSensor(JLREntity):
    def __init__(self, data):
        super().__init__(data, "vehicle")
        self._icon = "mdi:car"
        self._name = self._data.attributes.get("nickname") + " Info"
        _LOGGER.debug("Loading {} Sensors".format(self._name))

    @property
    def state(self):
        x = self._data.attributes.get("registrationNumber")
        return x

    @property
    def device_state_attributes(self):
        a = self._data.attributes
        attrs = {}

        for k, v in DATA_ATTRS_CAR_INFO.items():
            if a.get(v):
                attrs[k.title()] = a.get(v)

        attrs["Odometer"] = self._data.get_odometer()
        # If wakeup available add details
        if self._data.wakeup:
            attrs["State"] = self._data.wakeup.get("state").title()
            attrs["Next Update"] = self._data.wakeup.get("wakeupTime")

        attrs["Last Updated"] = self._data.status.get("lastUpdatedTime")
        return attrs


class JLRVehicleTyreSensor(JLREntity):
    def __init__(self, data):
        super().__init__(data, "tyre")
        self._icon = "mdi:car-tire-alert"
        self._name = self._data.attributes.get("nickname") + " Tyres"
        _LOGGER.debug("Loading {} Sensors".format(self._name))

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
            if s.get(v):
                attrs[k.title() + " Status"] = s.get(v).title()
        # Pressures
        for k, v in DATA_ATTRS_TYRE_PRESSURE.items():
            if s.get(v):
                attrs[k.title() + " Pressure (PSI)"] = __toPSI(s.get(v))

        return attrs


class JLRVehicleWindowSensor(JLREntity):
    def __init__(self, data):
        super().__init__(data, "window")
        self._icon = "mdi:car-door"
        self._name = self._data.attributes.get("nickname") + " Windows"
        _LOGGER.debug("Loading {} Sensors".format(self._name))

    @property
    def state(self):
        if all(
            [
                self._data.status.get(v) in ["CLOSED", "FALSE"]
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
            # Add sunroof status if applicable
            if k == "sunroof":
                if self._data.attributes.get("roofType") == "SUNROOF":
                    attrs[k.title()] = (
                        "Open"
                        if self._data.status.get("IS_SUNROOF_OPEN") == "TRUE"
                        else "Closed"
                    )
            else:
                attrs[k.title() + " Position"] = s.get(v).title()

        return attrs


class JLRVehicleServiceSensor(JLREntity):
    def __init__(self, data):
        super().__init__(data, "service_info")
        self._icon = "mdi:wrench"
        self._name = self._data.attributes.get("nickname") + " Service Info"
        _LOGGER.debug("Loading {} Sensors".format(self._name))

    @property
    def state(self):
        if all(
            [
                self._data.status.get(v) in SERVICE_STATUS_OK
                or self._data.status.get(v) == None
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
            if s.get(v):
                attrs[k.title()] = s.get(v).title()

        # Add metric sensors
        # TODO: Convert to local units
        for k, v in DATA_ATTRS_SERVICE_INFO.items():
            if s.get(v):
                attrs[k.title()] = s.get(v).title()
        return attrs


class JLRVehicleRangeSensor(JLREntity):
    def __init__(self, data):
        super().__init__(data, "range")
        self.fuel = self._data.attributes.get("fuelType")
        self._icon = (
            "mdi:speedometer" if self.fuel == FUEL_TYPE_BATTERY else "mdi:gas-station"
        )
        self._name = self._data.attributes.get("nickname") + " Range"
        _LOGGER.debug("Loading {} Sensors".format(self._name))

    @property
    def state(self):
        if self.fuel == FUEL_TYPE_BATTERY:
            if "Miles" in self._data.user_preferences.get("unitsOfMeasurement"):
                return self._data.status.get("EV_RANGE_ON_BATTERY_MILES", "0")
            else:
                return self._data.status.get("EV_RANGE_ON_BATTERY_KM", "0")
        else:
            return self._data.dist_to_user_prefs(
                self._data.status.get("DISTANCE_TO_EMPTY_FUEL")
            )

    @property
    def unit_of_measurement(self):
        if "Miles" in self._data.user_preferences.get("unitsOfMeasurement"):
            return LENGTH_MILES
        else:
            return LENGTH_KILOMETERS

    @property
    def device_state_attributes(self):
        attrs = {}
        attrs["Fuel Type"] = self.fuel

        if self.fuel == FUEL_TYPE_BATTERY:
            attrs["Battery Level"] = (
                self._data.status.get("EV_STATE_OF_CHARGE", "0") + UNIT_PERCENTAGE
            )
        else:
            # TODO: If fuelTankVolume is not none show remaining litres
            attrs["Fuel Level"] = (
                self._data.status.get("FUEL_LEVEL_PERC", "0") + UNIT_PERCENTAGE
            )
        return attrs


class JLREVChargeSensor(JLREntity):
    def __init__(self, data):
        super().__init__(data, "ev_battery")
        self._icon = "mdi:car-electric"
        self._name = self._data.attributes.get("nickname") + " EV Battery"
        _LOGGER.debug("Loading {} Sensors".format(self._name))

    @property
    def state(self):
        return self._data.status.get("EV_CHARGING_STATUS", "Unknown").title()

    @property
    def device_state_attributes(self):
        s = self._data.status
        attrs = {}

        units = (
            "MILES"
            if "Miles" in self._data.user_preferences.get("unitsOfMeasurement")
            else "KM"
        )

        for k, v in DATA_ATTRS_EV_CHARGE_INFO.items():
            if s.get(v):
                try:
                    attrs[k.title()] = s.get(v).format(units).title()
                except AttributeError:
                    attrs[k.title()] = s.get(v).title()
        return attrs
