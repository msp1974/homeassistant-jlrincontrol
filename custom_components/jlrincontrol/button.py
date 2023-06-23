"""Service call buttons"""
import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.exceptions import HomeAssistantError
from .coordinator import JLRIncontrolUpdateCoordinator


from .entity import JLREntity

from .const import DOMAIN, JLR_DATA, SUPPORTED_BUTTON_SERVICES

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Wiser climate device."""

    jlr_buttons = []
    coordinator = hass.data[DOMAIN][config_entry.entry_id][
        JLR_DATA
    ]  # Get Handler

    # Get list of supported services
    for vehicle in coordinator.vehicles:
        services = coordinator.vehicles[vehicle].supported_services

        _LOGGER.debug(
            "Setting up buttons for %s", coordinator.vehicles[vehicle].name
        )
        for service_code in SUPPORTED_BUTTON_SERVICES:
            if service_code in services:
                jlr_buttons.append(
                    JLRButton(coordinator, vehicle, service_code)
                )

    async_add_entities(jlr_buttons, True)


class JLRButton(JLREntity, ButtonEntity):
    """Button entity"""

    def __init__(
        self,
        coordinator: JLRIncontrolUpdateCoordinator,
        vin: str,
        service_code: str,
    ):
        """Initialize the sensor."""
        super().__init__(
            coordinator,
            vin,
            SUPPORTED_BUTTON_SERVICES[service_code].get("name"),
        )
        self.service_code = service_code
        self._icon = "mdi:fire"

    async def async_press(self):
        _LOGGER.debug("Pressed %s", self._name)
        if not self.coordinator.pin:
            raise HomeAssistantError("Unable to perform function.  No pin set")
        else:
            func = getattr(
                self.coordinator.get_vehicle(self.vin),
                SUPPORTED_BUTTON_SERVICES[self.service_code].get("function"),
            )
            # TODO: Add check for parameters needing passing!
            await self.hass.async_add_executor_job(func, self.coordinator.pin)
