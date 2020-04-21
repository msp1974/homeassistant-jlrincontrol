"""Support for JLR InControl Device Trackers."""
import logging
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.components.device_tracker import SOURCE_TYPE_GPS
from homeassistant.util import slugify
from . import DOMAIN, SIGNAL_STATE_UPDATED


_LOGGER = logging.getLogger(__name__)


async def async_setup_scanner(hass, config, async_see, discovery_info=None):
    data = hass.data[DOMAIN]
    _LOGGER.debug(
        "Loading device tracker for {}".format(data.attributes.get("nickname"))
    )

    tracker = JLRDeviceTracker(hass, async_see, data)
    await tracker.see_vehicle()
    async_dispatcher_connect(hass, SIGNAL_STATE_UPDATED, tracker.see_vehicle)
    return True


class JLRDeviceTracker:
    def __init__(self, hass, async_see, data) -> None:
        self._see = async_see
        self._data = data
        self._hass = hass

    async def see_vehicle(self):
        """Update the device info."""
        dev_id = slugify(self._data.attributes.get("nickname"))
        p = self._data.position
        gps = [
            round(p.get("position").get("latitude"), 8),
            round(p.get("position").get("longitude"), 8),
        ]

        _LOGGER.debug(
            "Updating {} Device Tracker".format(self._data.attributes.get("nickname"))
        )

        await self._see(
            dev_id=dev_id,
            host_name=self._data.attributes.get("nickname"),
            source_type=SOURCE_TYPE_GPS,
            gps=gps,
            icon="mdi:car",
        )
