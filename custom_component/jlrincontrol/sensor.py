"""Support for Dyson Pure Cool Link Sensors."""
import logging

# from homeassistant.const import STATE_OFF, UNIT_PERCENTAGE
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)
DOMAIN = "jlrincontrol"
DATA_KEY = DOMAIN


def setup_platform(hass, config, add_entities, discovery_info=None):
    data = hass.data[DATA_KEY]

    devices = []
    _LOGGER.debug("Loading sensors")

    devices.append(JLRVehicleSensor(data))

    add_entities(devices)


class JLRSensor(Entity):
    def __init__(self, data, sensor_type):
        """Create a new generic Dyson sensor."""
        self._name = None
        self._sensor_type = sensor_type

    @property
    def should_poll(self):
        """No polling needed."""
        return True

    @property
    def name(self):
        return self._name

    @property
    def icon(self):
        """Return the icon for this sensor."""
        return "mdi:cloud"

    @property
    def unique_id(self):
        """Return the sensor's unique id."""
        return f"JagXF-{self._sensor_type}"

    def update(self):
        _LOGGER.debug("Update requested")
        self.data.update()
        return True


class JLRVehicleSensor(JLRSensor):
    def __init__(self, data):
        super().__init__(data, "vehicle")
        self.data = data
        _LOGGER.debug(
            "Loading vehicles sensors for {}".format(
                self.data.attributes.get("registrationNumber")
            )
        )
        self._name = self.data.attributes.get("nickname")

    @property
    def state(self):
        x = self.data.attributes.get("registrationNumber")
        _LOGGER.debug("Reg - {}".format(x))
        return x

    @property
    def device_state_attributes(self):
        d = self.data.attributes
        attrs = {}
        attrs["Make"] = d.get("vehicleBrand")
        attrs["Model"] = d.get("vehicleType")
        attrs["Body"] = self.data.attributes.get("bodyType")
        attrs["Engine"] = self.data.attributes.get("engineCode")
        attrs["Fuel"] = self.data.attributes.get("fuelType")
        attrs["Transmission"] = self.data.attributes.get("gearboxCode")
        attrs["Year"] = self.data.attributes.get("modelYear")
        attrs["Colour"] = self.data.attributes.get("exteriorColorName")
        return attrs

