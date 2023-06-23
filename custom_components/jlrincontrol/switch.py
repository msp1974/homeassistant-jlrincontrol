"""Handles integration switches"""

import asyncio
import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN, JLR_DATA, SUPPORTED_SWITCH_SERVICES
from .coordinator import JLRIncontrolUpdateCoordinator
from .entity import JLREntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Wiser climate device."""

    jlr_switches = []
    coordinator: JLRIncontrolUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ][
        JLR_DATA
    ]  # Get Handler

    # Get list of supported services
    for vehicle in coordinator.vehicles:
        services = coordinator.vehicles[vehicle].supported_services

        _LOGGER.debug(
            "Setting up switches for %s", coordinator.vehicles[vehicle].name
        )
        for service_code in SUPPORTED_SWITCH_SERVICES:
            if service_code in services:
                jlr_switches.append(
                    JLRSwitch(coordinator, vehicle, service_code)
                )

    async_add_entities(jlr_switches, True)


class JLRSwitch(JLREntity, SwitchEntity):
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
            SUPPORTED_SWITCH_SERVICES[service_code].get("name"),
        )
        self.service_code = service_code
        self._icon = "mdi:fire"
        self._attr_is_on = True

    async def async_force_update(self, delay: int = 0):
        """Force update"""
        _LOGGER.debug("Update initiated by %s", self.name)
        if delay:
            await asyncio.sleep(delay)
        await self.coordinator.async_update_data()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        _LOGGER.debug(
            "%s switch update requested. State is %s",
            self.name,
            self._attr_is_on,
        )
        self._attr_is_on = False
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs):
        """Turn the device on."""
        _LOGGER.debug("Switch %s turned on", self._name)
        if not self.coordinator.pin:
            raise HomeAssistantError("Unable to perform function.  No pin set")
        else:
            func = getattr(
                self.get_vehicle_api(self.vin),
                SUPPORTED_SWITCH_SERVICES[self.service_code].get("on_func"),
            )
            # TODO: Add check for parameters needing passing!
            # await self.hass.async_add_executor_job(func, self.coordinator.pin)
            self._attr_is_on = True
            await self.async_force_update()

    async def async_turn_off(self, **kwargs):
        """Turn the device off."""
        _LOGGER.debug("Switch %s turned off", self._name)
        if not self.coordinator.pin:
            raise HomeAssistantError("Unable to perform function.  No pin set")
        else:
            func = getattr(
                self.get_vehicle_api(self.vin),
                SUPPORTED_SWITCH_SERVICES[self.service_code].get("on_func"),
            )
            # await self.hass.async_add_executor_job(func, self.coordinator.pin)
        self._attr_is_on = False
        await self.async_force_update()
