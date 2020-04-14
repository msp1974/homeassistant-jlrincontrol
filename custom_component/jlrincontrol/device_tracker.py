"""Support for JLR InControl Device Trackers."""
import logging
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.components.device_tracker import DeviceScanner
from homeassistant.util import slugify
from . import DOMAIN, SIGNAL_STATE_UPDATED


_LOGGER = logging.getLogger(__name__)


async def async_setup_scanner(hass, config, async_see, discovery_info=None):
    data = hass.data[DOMAIN]
    _LOGGER.debug("Device Tracker")

    tracker = JLRDeviceTracker(hass, async_see, data)
    await tracker.async_update()
    return True


class JLRDeviceTracker(DeviceScanner):
    def __init__(self, hass, async_see, data) -> None:
        self._see = async_see
        self._data = data
        self._hass = hass

    async def async_update(self):
        """Update the device info."""
        dev_id = slugify(self._data.attributes.get("nickname"))
        attrs = {"vin": self._data.vehicle.vin}
        p = self._data.position
        gps = [
            round(p.get("position").get("latitude"), 8),
            round(p.get("position").get("longitude"), 8),
        ]

        _LOGGER.debug("Updating vehicle location")

        await self._see(
            dev_id=dev_id,
            host_name=self._data.attributes.get("nickname"),
            gps=gps,
            attributes=attrs,
            icon="mdi:car",
        )

    async def async_added_to_hass(self):
        """Subscribe for update from the hub"""

        async def async_update_state():
            """Update sensor state."""
            await self.async_update()

        async_dispatcher_connect(self._hass, SIGNAL_STATE_UPDATED, async_update_state)
