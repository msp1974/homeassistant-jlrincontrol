"""Support for JLR InControl Sensors."""
import logging

# from homeassistant.const import STATE_OFF, UNIT_PERCENTAGE
from . import JLREntity, DOMAIN
from homeassistant.const import (
    UNIT_PERCENTAGE,
    LENGTH_KILOMETERS,
    LENGTH_MILES,
    LENGTH_METERS,
)
from homeassistant.util import dt, distance
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
    JLR_SERVICES,
    SERVICE_STATUS_OK,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    data = hass.data[DOMAIN]
    devices = []
    _LOGGER.debug("Loading Sensors")

    if discovery_info is None:
        return

    _LOGGER.debug(
        "Setting Up Sensors for - {}".format(
            data.vehicles[discovery_info].attributes.get("nickname")
        )
    )

    devices.append(JLRVehicleSensor(hass, discovery_info))
    devices.append(JLRVehicleWindowSensor(hass, discovery_info))
    devices.append(JLRVehicleAlarmSensor(hass, discovery_info))
    devices.append(JLRVehicleTyreSensor(hass, discovery_info))
    devices.append(JLRVehicleServiceSensor(hass, discovery_info))
    devices.append(JLRVehicleRangeSensor(hass, discovery_info))
    devices.append(JLRVehicleLastTripSensor(hass, discovery_info))

    # If EV show EV sensorl otherwise show fuel sensor
    if data.vehicles[discovery_info].attributes.get("fuelType") == FUEL_TYPE_BATTERY:
        devices.append(JLREVChargeSensor(hass, discovery_info))

    data.entities.extend(devices)
    async_add_entities(devices, True)


class JLRVehicleSensor(JLREntity):
    def __init__(self, hass, vin, *args):
        self._icon = "mdi:car"
        self._sensor_name = "info"
        super().__init__(hass, vin)

    @property
    def state(self):
        x = self._vehicle.attributes.get("registrationNumber")
        return x

    @property
    def device_state_attributes(self):
        a = self._vehicle.attributes
        attrs = {}

        for k, v in DATA_ATTRS_CAR_INFO.items():
            if a.get(v):
                attrs[k.title()] = a.get(v)

        attrs["Odometer"] = self.get_odometer(self._vehicle)

        if self._vehicle.status.get("lastUpdatedTime"):
            last_contacted = self.to_local_datetime(
                self._vehicle.status.get("lastUpdatedTime")
            )
            attrs["Last Contacted"] = last_contacted
            attrs["Last Contacted Age"] = dt.get_age(last_contacted) + " ago"
        return attrs


class JLRVehicleTyreSensor(JLREntity):
    def __init__(self, hass, vin, *args):
        self._icon = "mdi:car-tire-alert"
        self._sensor_name = "tyres"
        super().__init__(hass, vin)

    @property
    def state(self):
        # Convert to list of values from dict
        if all(
            [
                self._vehicle.status.get(v) == "NORMAL"
                for k, v in DATA_ATTRS_TYRE_STATUS.items()
            ]
        ):
            return "Ok"
        else:
            return "Warning"

    @property
    def device_state_attributes(self):
        # TODO: Convert to local units
        # TODO: Seems vehicles send in different units
        def __toPSI(bar):
            return round((int(bar) / 100) * 14.5038, 1)

        s = self._vehicle.status
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
    def __init__(self, hass, vin, *args):
        self._icon = "mdi:car-door"
        self._sensor_name = "windows"
        super().__init__(hass, vin)

    @property
    def state(self):
        if all(
            [
                self._vehicle.status.get(v) in ["CLOSED", "FALSE", "UNUSED"]
                for k, v in DATA_ATTRS_WINDOW_STATUS.items()
            ]
        ):
            return "Closed"
        else:
            return "Open"

    @property
    def device_state_attributes(self):
        s = self._vehicle.status
        attrs = {}
        for k, v in DATA_ATTRS_WINDOW_STATUS.items():
            # Add sunroof status if applicable
            if k == "sunroof":
                if self._vehicle.attributes.get("roofType") == "SUNROOF":
                    attrs[k.title()] = (
                        "Open"
                        if self._vehicle.status.get("IS_SUNROOF_OPEN") == "TRUE"
                        else "Closed"
                    )
            else:
                attrs[k.title() + " Position"] = s.get(v).title()

        return attrs


class JLRVehicleAlarmSensor(JLREntity):
    def __init__(self, hass, vin, *args):
        self._icon = "mdi:security"
        self._sensor_name = "alarm"
        super().__init__(hass, vin)

    @property
    def state(self):
        status = self._vehicle.status.get("THEFT_ALARM_STATUS")
        if status:
            status = status.replace("ALARM_", "")
            return status.replace("_", "").title()
        else:
            return "Not Supported"

    @property
    def device_state_attributes(self):
        attrs = {}
        return attrs


class JLRVehicleServiceSensor(JLREntity):
    def __init__(self, hass, vin, *args):
        self._icon = "mdi:wrench"
        self._sensor_name = "service info"
        super().__init__(hass, vin)

    @property
    def state(self):
        if all(
            [
                self._vehicle.status.get(v) in SERVICE_STATUS_OK
                or self._vehicle.status.get(v) == None
                for k, v in DATA_ATTRS_SERVICE_STATUS.items()
            ]
        ):
            return "Ok"
        else:
            return "Warning"

    @property
    def device_state_attributes(self):
        s = self._vehicle.status
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
    def __init__(self, hass, vin, *args):
        self._sensor_name = "range"
        super().__init__(hass, vin)
        self._units = self.get_distance_units()
        self._icon = (
            "mdi:speedometer" if self._fuel == FUEL_TYPE_BATTERY else "mdi:gas-station"
        )

    @property
    def state(self):
        if self._fuel == FUEL_TYPE_BATTERY:
            if self._units == LENGTH_KILOMETERS:
                return self._vehicle.status.get("EV_RANGE_ON_BATTERY_KM", "0")
            else:
                return self._vehicle.status.get("EV_RANGE_ON_BATTERY_MILES", "0")
        else:
            return round(
                distance.convert(
                    int(self._vehicle.status.get("DISTANCE_TO_EMPTY_FUEL")),
                    LENGTH_KILOMETERS,
                    self._units,
                )
            )

    @property
    def unit_of_measurement(self):
        return self._units

    @property
    def device_state_attributes(self):
        attrs = {}
        attrs["Fuel Type"] = self._fuel

        if self._fuel == FUEL_TYPE_BATTERY:
            attrs["Battery Level"] = (
                self._vehicle.status.get("EV_STATE_OF_CHARGE", "0") + UNIT_PERCENTAGE
            )
        else:
            # TODO: If fuelTankVolume is not none show remaining litres
            attrs["Fuel Level"] = (
                self._vehicle.status.get("FUEL_LEVEL_PERC", "0") + UNIT_PERCENTAGE
            )
        return attrs


class JLREVChargeSensor(JLREntity):
    def __init__(self, hass, vin, *args):
        self._sensor_name = "ev_battery"
        super().__init__(hass, vin)
        self._units = self.get_distance_units()
        self._icon = "mdi:car-electric"

    @property
    def state(self):
        return self._vehicle.status.get("EV_CHARGING_STATUS", "Unknown").title()

    @property
    def device_state_attributes(self):
        s = self._vehicle.status
        attrs = {}

        units = "KM" if self._units == LENGTH_KILOMETERS else "MILES"

        for k, v in DATA_ATTRS_EV_CHARGE_INFO.items():
            if s.get(v):
                try:
                    attrs[k.title()] = s.get(v).format(units).title()
                except AttributeError:
                    attrs[k.title()] = s.get(v).title()
        return attrs


class JLRVehicleLastTripSensor(JLREntity):
    def __init__(self, hass, vin, *args):
        self._sensor_name = "last trip"
        super().__init__(hass, vin)
        self._units = self.get_distance_units()
        self._icon = "mdi:map"

    @property
    def state(self):
        if self._vehicle.last_trip and self._vehicle.last_trip.get("tripDetails"):
            return round(
                distance.convert(
                    int(
                        self._vehicle.last_trip.get("tripDetails", "{}").get("distance")
                    ),
                    LENGTH_METERS,
                    self._units,
                )
            )
        else:
            return 0

    @property
    def unit_of_measurement(self):
        return self._units

    @property
    def device_state_attributes(self):
        attrs = {}
        if self._vehicle.last_trip:
            t = self._vehicle.last_trip.get("tripDetails")

            if t:
                attrs["start"] = self.to_local_datetime(t.get("startTime"))
                attrs["origin_latitude"] = t.get("startPosition").get("latitude")
                attrs["origin_longitude"] = t.get("startPosition").get("longitude")
                attrs["origin"] = t.get("startPosition").get("address")

                attrs["end"] = self.to_local_datetime(t.get("endTime"))
                attrs["destination_latitude"] = t.get("endPosition").get("latitude")
                attrs["destination_longitude"] = t.get("endPosition").get("longitude")
                attrs["destination"] = t.get("endPosition").get("address")
                if t.get("totalEcoScore"):
                    attrs["eco_score"] = t.get("totalEcoScore").get("score")
                attrs["average_speed"] = round(
                    distance.convert(
                        int(t.get("averageSpeed")), LENGTH_KILOMETERS, self._units,
                    )
                )

                if self._fuel == FUEL_TYPE_BATTERY:
                    attrs["average_consumption"] = round(
                        t.get("averageEnergyConsumption"), 1
                    )
                else:
                    if self._units == LENGTH_KILOMETERS:
                        attrs["average_consumption"] = round(
                            t.get("averageFuelConsumption"), 1
                        )
                    else:
                        attrs["average_consumption"] = round(
                            int(t.get("averageFuelConsumption")) * 2.35215, 1
                        )

            return attrs
