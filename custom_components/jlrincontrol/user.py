"""Class to handle JLR User."""

from dataclasses import dataclass
import json
import logging
from os.path import exists

import aiofiles

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant

from .const import CONF_PRESSURE_UNIT, JLR_TO_HASS_UNITS

_LOGGER = logging.getLogger(__name__)


@dataclass
class UserPreferenceUnits:
    """Holds unit prefs."""

    distance: str
    fuel: str
    temp: str
    pressure: str
    energy_regenerated: str
    energy_consumed: str

    def to_json(self):
        """Convert to json."""
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True)


@dataclass
class JLRUser:
    """Class to hold user info."""

    hass: HomeAssistant
    config_entry: ConfigEntry
    email: str
    first_name: str = ""
    middle_name: str = ""
    last_name: str = ""
    units: UserPreferenceUnits = None
    units_from_account: bool = False
    pressure_unit: str = "Default"

    async def async_get_user_info(self, connection) -> None:
        """Get user info."""
        self.pressure_unit = self.config_entry.options.get(
            CONF_PRESSURE_UNIT, "Default"
        )
        if not connection.user:
            user: dict = await connection.get_user_info()
        else:
            user: dict = connection.user

        _LOGGER.debug("USERINFO: %s", user)
        user = user.get("contact")

        received_uoms = str(
            user.get("userPreferences", {}).get("unitsOfMeasurement", "")
        )
        if uoms := received_uoms:
            # Save user prefs in .storage file
            await self.save_user_prefs(self.hass, self.email, uoms)
        else:
            uoms = await self.get_user_prefs(self.hass, self.email)

        if uoms:
            uoms = uoms.split(" ")
            user_prefs = UserPreferenceUnits(
                distance=JLR_TO_HASS_UNITS.get(
                    uoms[0], self.hass.config.units.length_unit
                ),
                fuel=JLR_TO_HASS_UNITS.get(uoms[1], self.hass.config.units.volume_unit),
                temp=JLR_TO_HASS_UNITS.get(
                    uoms[2], self.hass.config.units.temperature_unit
                ),
                pressure=self.hass.config.units.pressure_unit
                if self.pressure_unit == "Default"
                else self.pressure_unit,
                energy_regenerated=JLR_TO_HASS_UNITS.get(
                    uoms[4], UnitOfEnergy.KILO_WATT_HOUR
                ),
                energy_consumed=JLR_TO_HASS_UNITS.get(uoms[5], "Unknown"),
            )
        else:
            user_prefs = UserPreferenceUnits(
                distance=self.hass.config.units.length_unit,
                fuel=self.hass.config.units.volume_unit,
                temp=self.hass.config.units.temperature_unit,
                pressure=self.hass.config.units.pressure_unit,
                energy_regenerated=UnitOfEnergy.KILO_WATT_HOUR,
                energy_consumed=UnitOfEnergy.KILO_WATT_HOUR,
            )

        self.first_name = user.get("firstName", "Unkown")
        self.middle_name = user.get("middleName", "Unknown")
        self.last_name = user.get("lastName", "Unknown")
        self.units = user_prefs
        self.units_from_account = received_uoms is not None

        _LOGGER.debug("User Data: %s", self.units)

    async def save_user_prefs(self, hass: HomeAssistant, user_id, uoms) -> bool:
        """Write user preferences to file."""
        file = f"{hass.config.config_dir}/.storage/jlrincontrol_data_{user_id}"
        # Write to config file
        async with aiofiles.open(file, mode="w") as config_file:
            # try:
            await config_file.write(uoms)
        return True

    async def get_user_prefs(self, hass: HomeAssistant, user_id) -> dict:
        """Get user prefs from file."""
        file = f"{hass.config.config_dir}/.storage/jlrincontrol_data_{user_id}"
        if exists(file):
            async with aiofiles.open(file, mode="r") as user_pref_file:
                contents = await user_pref_file.read()
                if contents:
                    uoms = contents
            return uoms
