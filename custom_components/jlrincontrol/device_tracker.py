"""Support for JLR InControl Device Trackers."""
import logging
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.components.device_tracker import SOURCE_TYPE_GPS
from homeassistant.components.device_tracker.config_entry import TrackerEntity
from .const import JLR_DATA, DOMAIN
from .entity import JLREntity


_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    data = hass.data[DOMAIN][config_entry.entry_id][JLR_DATA]
    devices = []

    for vehicle in data.vehicles:
        if data.vehicles[vehicle].position:
            devices.append(JLRDeviceTracker(hass, data, vehicle))

        else:
            _LOGGER.debug(
                "Vehicle {} is not providing any position information.".format(
                    data.vehicles[vehicle].attributes.get("nickname")
                )
                + " No device trakcer will be created."
            )
    async_add_entities(devices, True)


class JLRDeviceTracker(JLREntity, TrackerEntity):
    def __init__(self, hass, data, vin) -> None:
        self._position = None
        self._latitude = None
        self._longitude = None
        self._icon = "mdi:car-connected"
        self._sensor_name = "device tracker"
        super().__init__(hass, data, vin)

    async def async_update(self):
        """Update the device info."""
        _LOGGER.debug("Updating {}".format(self._name))
        try:
            self._position = self._vehicle.position.get("position")

            if self._position:
                self._latitude = round(self._position.get("latitude"), 8)
                self._longitude = round(self._position.get("longitude"), 8)
        except Exception as ex:
            _LOGGER.debug(
                "Unable to update device tracker for {}. Error is {}".format(
                    self._name, ex
                )
            )

    @property
    def extra_state_attributes(self):
        attrs = {}

        try:
            loc_name = self._hass.async_add_exexutor_job(
                self._data.connection.reverse_geocode,
                (self._latitude, self._longitude),
            )
            attrs["location"] = loc_name.get("formattedAddress")
        except Exception:
            pass
        attrs["speed"] = self._position.get("speed")
        attrs["heading"] = self._position.get("heading")

        return attrs

    @property
    def latitude(self) -> float:
        """Return latitude value of the device."""
        return self._latitude

    @property
    def longitude(self) -> float:
        """Return longitude value of the device."""
        return self._longitude

    @property
    def source_type(self):
        """Return the source type, eg gps or router, of the device."""
        return SOURCE_TYPE_GPS
