"""Support for JLR InControl Sensors."""
import logging

# from homeassistant.const import STATE_OFF, UNIT_PERCENTAGE
from homeassistant.const import (
    DEVICE_CLASS_BATTERY,
    PERCENTAGE,
    LENGTH_KILOMETERS,
    LENGTH_METERS,
    PRESSURE_PA,
    PRESSURE_BAR,
)
from homeassistant.helpers import icon
from homeassistant.util import dt, distance, pressure
from .const import (
    DOMAIN,
    DATA_ATTRS_CAR_INFO,
    DATA_ATTRS_EV_CHARGE_INFO,
    DATA_ATTRS_TYRE_STATUS,
    DATA_ATTRS_TYRE_PRESSURE,
    DATA_ATTRS_WINDOW_STATUS,
    DATA_ATTRS_SERVICE_STATUS,
    DATA_ATTRS_SERVICE_INFO,
    FUEL_TYPE_BATTERY,
    JLR_CHARGE_METHOD_TO_HA,
    JLR_CHARGE_STATUS_TO_HA,
    JLR_DATA,
    SERVICE_STATUS_OK,
)
from .entity import JLREntity
from .config_flow import CONF_ALL_DATA_SENSOR

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    data = hass.data[DOMAIN][config_entry.entry_id][JLR_DATA]

    devices = []
    _LOGGER.debug("Loading Sensors")

    for vehicle in data.vehicles:
        _LOGGER.debug(
            "Setting Up Sensors for - {}".format(
                data.vehicles[vehicle].attributes.get("nickname")
            )
        )

        devices.append(JLRVehicleSensor(hass, data, vehicle))
        devices.append(JLRVehicleWindowSensor(hass, data, vehicle))
        devices.append(JLRVehicleAlarmSensor(hass, data, vehicle))
        devices.append(JLRVehicleTyreSensor(hass, data, vehicle))
        devices.append(JLRVehicleServiceSensor(hass, data, vehicle))
        devices.append(JLRVehicleRangeSensor(hass, data, vehicle))
        devices.append(JLRVehicleStatusSensor(hass, data, vehicle))

        if config_entry.options.get(CONF_ALL_DATA_SENSOR):
            devices.append(JLRVehicleAllDataSensor(hass, data, vehicle))

        # If EV show EV sensorl otherwise show fuel sensor
        if (
            data.vehicles[vehicle].attributes.get("fuelType")
            == FUEL_TYPE_BATTERY
        ):
            devices.append(JLREVChargeSensor(hass, data, vehicle))
            devices.append(JLREVBatterySensor(hass, data, vehicle))

        # Show last trip sensor is privacy mode off and data exists
        if data.vehicles[vehicle].last_trip:
            devices.append(JLRVehicleLastTripSensor(hass, data, vehicle))
        else:
            _LOGGER.debug(
                "Not loading Last Trip sensor due to privacy mode or no data"
            )

    data.entities.extend(devices)
    async_add_entities(devices, True)


class JLRVehicleAllDataSensor(JLREntity):
    def __init__(self, hass, data, vin):
        self._icon = "mdi:cloud"
        self._sensor_name = "all info"
        super().__init__(hass, data, vin)

    @property
    def state(self):
        if self._vehicle.status.get("lastUpdatedTime"):
            last_contacted = self.to_local_datetime(
                self._vehicle.status.get("lastUpdatedTime")
            )
            return dt.get_age(last_contacted) + " ago"
        return "Unknown"

    @property
    def extra_state_attributes(self):
        attrs = {}

        # Vehicle Attributes
        attributes = self._vehicle.attributes.copy()

        # Remove Capabilities
        if attributes.get("capabilities"):
            del attributes["capabilities"]

        # Remove Services
        if attributes.get("availableServices"):
            del attributes["availableServices"]

        attrs["attributes"] = dict(sorted(attributes.items()))

        # Vehicle Status
        s = {}
        for k, v in self._vehicle.status.copy().items():
            k = k[0].lower() + k.title().replace("_", "")[1:]
            s[k] = v
        attrs["status"] = dict(sorted(s.items()))

        # Vehicle Position
        attrs["position"] = dict(sorted(self._vehicle.position.items()))

        return attrs


class JLRVehicleSensor(JLREntity):
    def __init__(self, hass, data, vin):
        self._icon = "mdi:car-info"
        self._sensor_name = "info"
        super().__init__(hass, data, vin)

    @property
    def state(self):
        x = self._vehicle.attributes.get("registrationNumber")
        return x

    @property
    def extra_state_attributes(self):
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
    def __init__(self, hass, data, vin):
        self._icon = "mdi:car-tire-alert"
        self._sensor_name = "tyres"
        super().__init__(hass, data, vin)
        self._units = self.get_pressure_units()

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
    def extra_state_attributes(self):
        s = self._vehicle.status
        attrs = {}

        # Statuses
        for k, v in DATA_ATTRS_TYRE_STATUS.items():
            if s.get(v):
                attrs[k.title() + " Status"] = s.get(v).title()

        # Hass lacks proper pressure conversions/units definitions.
        # So need to deal with here
        # Pressures
        for k, v in DATA_ATTRS_TYRE_PRESSURE.items():

            if s.get(v):
                tyre_pressure = int(s.get(v))
                # Some vehicles send in kPa*10, others in kPa. Ensure in kPa
                if tyre_pressure > 1000:
                    tyre_pressure = tyre_pressure / 10

                # Convert to local units - metric = bar, imperial = psi
                if self._units == PRESSURE_BAR:
                    attrs[
                        k.title() + " Pressure ({})".format(self._units)
                    ] = round(tyre_pressure / 100, 2)
                else:
                    attrs[
                        k.title() + " Pressure ({})".format(self._units)
                    ] = round(
                        pressure.convert(
                            tyre_pressure * 1000, PRESSURE_PA, self._units
                        ),
                        1,
                    )

        return attrs


class JLRVehicleWindowSensor(JLREntity):
    def __init__(self, hass, data, vin):
        self._icon = "mdi:car-door"
        self._sensor_name = "windows"
        super().__init__(hass, data, vin)

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
    def extra_state_attributes(self):
        s = self._vehicle.status
        attrs = {}
        for k, v in DATA_ATTRS_WINDOW_STATUS.items():
            # Add sunroof status if applicable
            if k == "sunroof":
                if self._vehicle.attributes.get("roofType") == "SUNROOF":
                    attrs[k.title()] = (
                        "Open"
                        if self._vehicle.status.get("IS_SUNROOF_OPEN")
                        == "TRUE"
                        else "Closed"
                    )
            else:
                attrs[k.title() + " Position"] = s.get(v).title()

        return attrs


class JLRVehicleAlarmSensor(JLREntity):
    def __init__(self, hass, data, vin):
        self._icon = "mdi:security"
        self._sensor_name = "alarm"
        super().__init__(hass, data, vin)

    @property
    def state(self):
        status = self._vehicle.status.get("THEFT_ALARM_STATUS")
        if status:
            status = status.replace("ALARM_", "")
            return status.replace("_", "").title()
        else:
            return "Not Supported"

    @property
    def extra_state_attributes(self):
        attrs = {}
        return attrs


class JLRVehicleServiceSensor(JLREntity):
    def __init__(self, hass, data, vin):
        self._icon = "mdi:wrench"
        self._sensor_name = "service info"
        super().__init__(hass, data, vin)

    @property
    def state(self):
        if all(
            [
                self._vehicle.status.get(v) in SERVICE_STATUS_OK
                or self._vehicle.status.get(v) is None
                for k, v in DATA_ATTRS_SERVICE_STATUS.items()
            ]
        ):
            return "Ok"
        else:
            return "Warning"

    @property
    def extra_state_attributes(self):
        s = self._vehicle.status
        attrs = {}
        for k, v in DATA_ATTRS_SERVICE_STATUS.items():
            if s.get(v):
                attrs[k.title()] = s.get(v).replace("_", " ").title()

        # Add metric sensors
        # TODO: Convert to local units
        for k, v in DATA_ATTRS_SERVICE_INFO.items():
            if s.get(v):
                attrs[k.title()] = s.get(v).title()
        return attrs


class JLRVehicleRangeSensor(JLREntity):
    def __init__(self, hass, data, vin):
        self._sensor_name = "range"
        super().__init__(hass, data, vin)
        self._units = self.get_distance_units()
        self._icon = (
            "mdi:speedometer"
            if self._fuel == FUEL_TYPE_BATTERY
            else "mdi:gas-station"
        )

    @property
    def state(self):
        if self._fuel == FUEL_TYPE_BATTERY:
            if self._units == LENGTH_KILOMETERS:
                return self._vehicle.status.get("EV_RANGE_ON_BATTERY_KM", "0")
            else:
                return self._vehicle.status.get(
                    "EV_RANGE_ON_BATTERY_MILES", "0"
                )
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
    def extra_state_attributes(self):
        attrs = {}
        attrs["Fuel Type"] = self._fuel

        if self._fuel == FUEL_TYPE_BATTERY:
            attrs["Battery Level"] = (
                self._vehicle.status.get("EV_STATE_OF_CHARGE", "0")
                + PERCENTAGE
            )
        else:
            # TODO: If fuelTankVolume is not none show remaining litres
            attrs["Fuel Level"] = (
                self._vehicle.status.get("FUEL_LEVEL_PERC", "0")
                + PERCENTAGE
            )
        return attrs


class JLREVChargeSensor(JLREntity):
    def __init__(self, hass, data, vin):
        self._sensor_name = "ev_battery"
        super().__init__(hass, data, vin)
        self._units = self.get_distance_units()
        self._icon = "mdi:car-electric"

    @property
    def state(self):
        return self._vehicle.status.get(
            "EV_CHARGING_STATUS", "Unknown"
        ).title()

    @property
    def extra_state_attributes(self):
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


class JLREVBatterySensor(JLREntity):
    def __init__(self, hass, data, vin):
        self._sensor_name = "battery"
        super().__init__(hass, data, vin)
        self._units = self.get_distance_units()
        self._charging_state = False

    @property
    def state(self):
        return self._vehicle.status.get("EV_STATE_OF_CHARGE", 0)

    @property
    def device_class(self):
        """Return the class of the sensor."""
        return DEVICE_CLASS_BATTERY

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity."""
        return "%"

    @property
    def icon(self):
        return icon.icon_for_battery_level(
            int(self._vehicle.status.get("EV_STATE_OF_CHARGE", 0)),
            self._charging_state,
        )

    @property
    def extra_state_attributes(self):
        attrs = {}
        units = "KM" if self._units == LENGTH_KILOMETERS else "MILES"
        s = self._vehicle.status

        # Charging status
        self._charging_state = (
            True
            if s.get("EV_CHARGING_STATUS")
            in ["CHARGING", "WAITINGTOCHARGE", "INITIALIZATION"]
            else False
        )
        attrs["Charging"] = self._charging_state

        # Max SOC Values Set
        if (
            s.get("EV_ONE_OFF_MAX_SOC_CHARGE_SETTING_CHOICE")
            and s.get("EV_ONE_OFF_MAX_SOC_CHARGE_SETTING_CHOICE") != "CLEAR"
        ):
            attrs["Max SOC"] = s.get(
                "EV_ONE_OFF_MAX_SOC_CHARGE_SETTING_CHOICE"
            )
        elif (
            s.get("EV_PERMANENT_MAX_SOC_CHARGE_SETTING_CHOICE")
            and s.get("EV_PERMANENT_MAX_SOC_CHARGE_SETTING_CHOICE") != "CLEAR"
        ):
            attrs["Max SOC"] = s.get(
                "EV_PERMANENT_MAX_SOC_CHARGE_SETTING_CHOICE"
            )

        attrs["Charging State"] = JLR_CHARGE_STATUS_TO_HA.get(
            s.get("EV_CHARGING_STATUS"),
            s.get("EV_CHARGING_STATUS", "Unknown").title(),
        )

        attrs["Charging Method"] = JLR_CHARGE_METHOD_TO_HA.get(
            s.get("EV_CHARGING_METHOD"),
            s.get("EV_CHARGING_METHOD", "Unknown").title(),
        )

        attrs["Minutes to Full Charge"] = s.get(
            "EV_MINUTES_TO_FULLY_CHARGED", "Unknown"
        )

        attrs["Charging Rate ({}/h)".format(units.lower())] = s.get(
            "EV_CHARGING_RATE_{}_PER_HOUR".format(units), "Unknown"
        )

        attrs["Charging Rate (%/h)"] = s.get(
            "EV_CHARGING_RATE_SOC_PER_HOUR", "Unknown"
        )

        # Last Charge Amount
        attrs["Last Charge Energy (kWh)"] = round(
            int(s.get("EV_ENERGY_CONSUMED_LAST_CHARGE_KWH", 0)) / 10, 1
        )

        return attrs


class JLRVehicleLastTripSensor(JLREntity):
    def __init__(self, hass, data, vin):
        self._sensor_name = "last trip"
        super().__init__(hass, data, vin)
        self._units = self.get_distance_units()
        self._icon = "mdi:map"

    @property
    def state(self):
        if self._vehicle.last_trip and self._vehicle.last_trip.get(
            "tripDetails"
        ):
            return round(
                distance.convert(
                    int(
                        self._vehicle.last_trip.get("tripDetails", "{}").get(
                            "distance"
                        )
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
    def extra_state_attributes(self):
        attrs = {}
        if self._vehicle.last_trip:
            t = self._vehicle.last_trip.get("tripDetails")

            if t:
                attrs["start"] = self.to_local_datetime(t.get("startTime"))
                attrs["origin_latitude"] = t.get("startPosition").get(
                    "latitude"
                )
                attrs["origin_longitude"] = t.get("startPosition").get(
                    "longitude"
                )
                attrs["origin"] = t.get("startPosition").get("address")

                attrs["end"] = self.to_local_datetime(t.get("endTime"))
                attrs["destination_latitude"] = t.get("endPosition").get(
                    "latitude"
                )
                attrs["destination_longitude"] = t.get("endPosition").get(
                    "longitude"
                )
                attrs["destination"] = t.get("endPosition").get("address")
                if t.get("totalEcoScore"):
                    attrs["eco_score"] = t.get("totalEcoScore").get("score")
                attrs["average_speed"] = round(
                    distance.convert(
                        int(t.get("averageSpeed")),
                        LENGTH_KILOMETERS,
                        self._units,
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


class JLRVehicleStatusSensor(JLREntity):
    def __init__(self, hass, data, vin):
        self._sensor_name = "status"
        super().__init__(hass, data, vin)
        self._icon = "mdi:car"

    @property
    def state(self):
        status = self._vehicle.status.get("VEHICLE_STATE_TYPE")

        if status:
            return status.replace("_", " ").title()
        else:
            return "Unknown"

    @property
    def extra_state_attributes(self):
        attrs = {}
        return attrs
