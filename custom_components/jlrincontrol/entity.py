import logging
from homeassistant.const import (
    LENGTH_KILOMETERS,
    PRESSURE_BAR,
    PRESSURE_PA,
    PRESSURE_PSI,
)
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity
from homeassistant.util import dt
from .const import DOMAIN, SIGNAL_STATE_UPDATED

_LOGGER = logging.getLogger(__name__)


class JLREntity(Entity):
    def __init__(self, hass, data, vin):
        """Create a new generic JLR sensor."""
        self._hass = hass
        self._data = data
        self._vin = vin
        self._vehicle = self._data.vehicles[self._vin]
        self._name = (
            self._vehicle.attributes.get("nickname")
            + " "
            + self._sensor_name.title()
        )
        self._engine_type = self._vehicle.engine_type
        self._fuel = self._vehicle.attributes.get("fuelType")
        self._entity_prefix = (
            self._vehicle.attributes.get("vehicleBrand")
            + self._vehicle.attributes.get("vehicleType")
            + "-"
            + self._vin[-6:]
        )

        _LOGGER.debug("Loading {} Sensor".format(self._name))

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def name(self):
        return self._name

    @property
    def icon(self):
        """Return the icon for this sensor."""
        return self._icon or "mdi:cloud"

    @property
    def vehicle(self):
        return self._vehicle

    @property
    def unique_id(self):
        """Return the sensor's unique id."""
        return f"{self._entity_prefix}-{self._sensor_name}"

    @property
    def device_info(self):
        """Return device specific attributes."""
        return {
            "identifiers": {(DOMAIN, self._vin)},
        }

    @property
    def assumed_state(self):
        """Return true if unable to access real state of entity."""
        return True

    async def async_update(self):
        _LOGGER.debug("Updating {}".format(self._name))
        return True

    async def async_added_to_hass(self):
        """Subscribe for update from the hub"""

        async def async_update_state():
            """Update sensor state."""
            await self.async_update_ha_state(True)

        self.async_on_remove(
            async_dispatcher_connect(
                self._hass, SIGNAL_STATE_UPDATED, async_update_state
            )
        )

    def to_local_datetime(self, datetime: str):
        try:
            return dt.as_local(dt.parse_datetime(datetime))
        except Exception:
            return None

    def get_distance_units(self):
        if self._data.distance_unit and self._data.distance_unit != "Default":
            return self._data.distance_unit
        else:
            return self._hass.config.units.length_unit

    def get_pressure_units(self):
        if self._data.pressure_unit and self._data.pressure_unit != "Default":
            return self._data.pressure_unit
        else:
            if self._hass.config.units.pressure_unit == PRESSURE_PA:
                return PRESSURE_BAR
            else:
                return PRESSURE_PSI

    def get_odometer(self, vehicle):
        self.units = self.get_distance_units()
        if self.units == LENGTH_KILOMETERS:
            return int(int(vehicle.status.get("ODOMETER_METER")) / 1000)
        else:
            return int(vehicle.status.get("ODOMETER_MILES"))
