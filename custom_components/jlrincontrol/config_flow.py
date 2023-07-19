"""
Config Flow for JLR InControl

"""
import logging
import urllib
import uuid

import jlrpy
import voluptuous as vol
from homeassistant import config_entries, exceptions
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_PIN,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    PRESSURE_BAR,
    PRESSURE_PSI,
)
from homeassistant.core import callback

from .const import (
    CONF_DEFAULT_CLIMATE_TEMP,
    CONF_DEFAULT_SERVICE_DURATION,
    CONF_DEVICE_ID,
    CONF_HEALTH_UPDATE_INTERVAL,
    CONF_PRESSURE_UNIT,
    CONF_USE_CHINA_SERVERS,
    DEFAULT_HEATH_UPDATE_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)

UNIQUE_ID = "unique_id"
DEVICE_ID = "device_id"

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_USE_CHINA_SERVERS, default=False): bool,
        vol.Required(CONF_DEVICE_ID, default=str(uuid.uuid4())): str,
    }
)


@callback
def configured_instances(hass):
    """Return a set of configured JLR InControl instances."""
    return {entry.title for entry in hass.config_entries.async_entries(DOMAIN)}


async def validate_input(hass, data):
    """Validate the user input allows us to connect"""

    try:
        connection = await hass.async_add_executor_job(
            jlrpy.Connection,
            data[CONF_USERNAME],
            data[CONF_PASSWORD],
            "",
            "",
            data[CONF_USE_CHINA_SERVERS],
        )
    except urllib.error.HTTPError as ex:
        if ex.code > 400 and ex.code < 500:
            raise InvalidAuth from ex
        raise CannotConnect from ex
    except ValueError as ex:
        raise InvalidAuth from ex
    except Exception as ex:
        raise CannotConnect from ex

    if not connection.vehicles or len(connection.vehicles) == 0:
        raise NoVehicles

    return {
        "title": connection.email,
        UNIQUE_ID: f"{DOMAIN}-{data[CONF_USERNAME]}",
    }


@config_entries.HANDLERS.register(DOMAIN)
class JLRInControlFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handles config setup"""

    VERSION = 2
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        """Initialize the jlrincontrol flow."""
        self.conf = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return JLRInControlOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            if self._username_already_configured(user_input):
                return self.async_abort(reason="already_configured")

            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except NoVehicles:
                errors["base"] = "no_vehicles"
            except Exception as ex:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception - %s", ex)
                errors["base"] = "unknown"

            if "base" not in errors:
                await self.async_set_unique_id(info[UNIQUE_ID])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    async def async_step_import(self, import_data):
        """Handle import."""
        return await self.async_step_user(import_data)

    def _username_already_configured(self, user_input):
        """See if we already have a username matching user input configured."""
        existing_username = {
            entry.data[CONF_USERNAME] for entry in self._async_current_entries()
        }
        return user_input[CONF_USERNAME] in existing_username


class JLRInControlOptionsFlowHandler(config_entries.OptionsFlow):
    """Handles JLRIncontrol options"""

    def __init__(self, config_entry):
        """Initialize deCONZ options flow."""
        self.config_entry = config_entry
        self.options = dict(config_entry.options)

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        return await self.async_step_user(user_input)

    async def async_step_user(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        data_schema = vol.Schema(
            {
                vol.Required(CONF_PIN, default=self.options.get(CONF_PIN, "0000")): str,
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=self.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): (vol.All(vol.Coerce(int), vol.Clamp(min=MIN_SCAN_INTERVAL))),
                vol.Required(
                    CONF_HEALTH_UPDATE_INTERVAL,
                    default=self.options.get(
                        CONF_HEALTH_UPDATE_INTERVAL,
                        DEFAULT_HEATH_UPDATE_INTERVAL,
                    ),
                ): vol.Coerce(int),
                vol.Required(
                    CONF_PRESSURE_UNIT,
                    default=self.options.get(CONF_PRESSURE_UNIT, PRESSURE_BAR),
                ): vol.In(["Default", PRESSURE_BAR, PRESSURE_PSI]),
                vol.Required(
                    CONF_DEFAULT_CLIMATE_TEMP,
                    default=self.options.get(CONF_DEFAULT_CLIMATE_TEMP, 21),
                ): vol.Coerce(int),
                vol.Required(
                    CONF_DEFAULT_SERVICE_DURATION,
                    default=self.options.get(CONF_DEFAULT_SERVICE_DURATION, 24),
                ): vol.Coerce(int),
            }
        )

        return self.async_show_form(step_id="user", data_schema=data_schema)


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""


class NoVehicles(exceptions.HomeAssistantError):
    """Error to indicate no vehicles on account."""
