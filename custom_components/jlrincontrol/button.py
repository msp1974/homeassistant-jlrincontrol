"""Service call buttons."""

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN, JLR_DATA, SUPPORTED_BUTTON_SERVICES
from .entity import JLREntity
from .services import JLRService
from .util import requires_pin

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
):
    """Set up Wiser climate device."""

    jlr_buttons = []
    coordinator = hass.data[DOMAIN][config_entry.entry_id][JLR_DATA]  # Get Handler

    # Get list of supported services
    for vehicle in coordinator.vehicles:
        services = coordinator.vehicles[vehicle].supported_services

        _LOGGER.debug("Setting up buttons for %s", coordinator.vehicles[vehicle].name)
        for service_code in SUPPORTED_BUTTON_SERVICES:
            if service_code in services:
                jlr_buttons.append(JLRButton(coordinator, vehicle, service_code))

    async_add_entities(jlr_buttons, True)


class JLRButton(JLREntity, ButtonEntity):
    """Button entity."""

    def __init__(
        self,
        coordinator,
        vin: str,
        service_code: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            coordinator,
            vin,
            SUPPORTED_BUTTON_SERVICES[service_code].get("name"),
        )
        self.service_code = service_code
        self._icon = SUPPORTED_BUTTON_SERVICES[service_code].get("icon")

    async def async_press(self):
        """Button press function."""
        _LOGGER.debug("Pressed %s", self._name)
        if (
            requires_pin(SUPPORTED_BUTTON_SERVICES, self.service_code)
            and not self.vehicle.pin
        ):
            raise HomeAssistantError("Unable to perform function.  No pin set")

        service = SUPPORTED_BUTTON_SERVICES[self.service_code].get("service")
        jlr_service = JLRService(self.coordinator, self.vin, service)
        await jlr_service.async_call_service()
        await self.async_force_update()
