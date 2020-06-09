"""
Config Flow for JLR InControl

"""
import logging
import voluptuous as vol
from homeassistant import config_entries, exceptions
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_PIN,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    LENGTH_KILOMETERS,
    LENGTH_MILES,
    PRESSURE_BAR,
    PRESSURE_PSI,
)
from homeassistant.core import callback
import jlrpy

from .const import (
    DOMAIN,
    DEFAULT_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    DEFAULT_HEATH_UPDATE_INTERVAL,
)

CONF_DEBUG_DATA = "debug_data"
CONF_DISTANCE_UNIT = "distance_unit"
CONF_PRESSURE_UNIT = "pressure_unit"
CONF_HEALTH_UPDATE_INTERVAL = "health_update_interval"

_LOGGER = logging.getLogger(__name__)

data_schema = {
    vol.Required(CONF_USERNAME): str,
    vol.Required(CONF_PASSWORD): str,
}


@callback
def configured_instances(hass):
    """Return a set of configured JLR InControl instances."""
    return {entry.title for entry in hass.config_entries.async_entries(DOMAIN)}


def _test_connection(user, password, device_id=""):
    try:
        connection = jlrpy.Connection(user, password, device_id=device_id)
    except ValueError as err:
        raise InvalidAuth(err.args[0])

    return connection


async def validate_input(hass, data):
    user = data[CONF_USERNAME]
    password = data[CONF_PASSWORD]
    device_id = data.get("device_id")

    connection = await hass.async_add_executor_job(
        _test_connection, user, password, device_id
    )

    if not connection or not connection.refresh_token:
        raise CannotConnect

    return {
        "title": connection.email,
        "device_id": connection.device_id,
    }


@config_entries.HANDLERS.register(DOMAIN)
class JLRInControlFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    # The schema version of the entries that it creates
    # Home Assistant will call your migrate method if the version changes
    # (this is not implemented yet)
    VERSION = 1
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
        """
        Handle a JLR InControl config flow start.
        Manage device specific parameters.
        """
        errors = {}
        info = None
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

            if not errors:
                await self.async_set_unique_id(
                    f"{DOMAIN}-{info['device_id']}", raise_on_progress=False
                )
                self._abort_if_unique_id_configured()
                user_input["device_id"] = info["device_id"]
                return self.async_create_entry(
                    title=info["title"], data=user_input
                )

        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(data_schema), errors={},
        )

    async def async_step_import(self, import_data):
        """
        Import wiser config from configuration.yaml.
        Triggered by async_setup only if a config entry doesn't already exist.
        """
        return await self.async_step_user(import_data)


class JLRInControlOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        """Initialize deCONZ options flow."""
        self.config_entry = config_entry
        self.options = dict(config_entry.options)

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_PIN, default=self.options.get(CONF_PIN)
                ): str,
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=self.options.get(
                        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                    ),
                ): (
                    vol.All(vol.Coerce(int), vol.Clamp(min=MIN_SCAN_INTERVAL))
                ),
                vol.Optional(
                    CONF_HEALTH_UPDATE_INTERVAL,
                    default=self.options.get(
                        CONF_HEALTH_UPDATE_INTERVAL,
                        DEFAULT_HEATH_UPDATE_INTERVAL,
                    ),
                ): vol.Coerce(int),
                vol.Optional(
                    CONF_DISTANCE_UNIT,
                    default=self.options.get(
                        CONF_DISTANCE_UNIT, LENGTH_KILOMETERS
                    ),
                ): vol.In(["Default", LENGTH_KILOMETERS, LENGTH_MILES]),
                vol.Optional(
                    CONF_PRESSURE_UNIT,
                    default=self.options.get(CONF_PRESSURE_UNIT, PRESSURE_BAR),
                ): vol.In(["Default", PRESSURE_BAR, PRESSURE_PSI]),
                vol.Optional(
                    CONF_DEBUG_DATA,
                    default=self.options.get(CONF_DEBUG_DATA, False),
                ): bool,
            }
        )

        return self.async_show_form(step_id="user", data_schema=data_schema)


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""
