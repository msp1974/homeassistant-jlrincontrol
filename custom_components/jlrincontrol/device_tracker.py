"""Support for JLR InControl Device Trackers."""
import logging
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.components.device_tracker import SOURCE_TYPE_GPS
from homeassistant.util import slugify
from . import DOMAIN, SIGNAL_STATE_UPDATED


_LOGGER = logging.getLogger(__name__)


async def async_setup_scanner(hass, config, async_see, discovery_info=None):
    data = hass.data[DOMAIN]
    if discovery_info is None:
        return

    _LOGGER.debug(
        "Loading Device Tracker for - {}".format(
            data.vehicles[discovery_info].attributes.get("nickname")
        )
    )

    tracker = JLRDeviceTracker(hass, async_see, discovery_info)
    await tracker.see_vehicle()
    async_dispatcher_connect(hass, SIGNAL_STATE_UPDATED, tracker.see_vehicle)
    return True


class JLRDeviceTracker:
    def __init__(self, hass, async_see, vin) -> None:
        self._hass = hass
        self._see = async_see
        self._data = self._hass.data[DOMAIN]
        self._vin = vin
        self._vehicle = self._data.vehicles[self._vin]
        self._name = self._vehicle.attributes.get("nickname")

    async def see_vehicle(self):
        """Update the device info."""
        dev_id = slugify(self._name)
        p = self._vehicle.position.get("position")

        if p:
            gps = [
                round(p.get("latitude"), 8),
                round(p.get("longitude"), 8),
            ]

            attrs = {}
            try:
                loc_name = self._hass.async_add_exexutor_job(
                    self._data.connection.reverse_geocode, (gps[0], gps[1])
                )
                attrs["location"] = loc_name.get("formattedAddress")
            except:
                pass
            attrs["speed"] = p.get("speed")
            attrs["heading"] = p.get("heading")

            _LOGGER.debug("Updating {} Device Tracker".format(self._name))

            await self._see(
                dev_id=dev_id,
                host_name=self._name,
                source_type=SOURCE_TYPE_GPS,
                gps=gps,
                icon="mdi:car",
                attributes=attrs,
            )
