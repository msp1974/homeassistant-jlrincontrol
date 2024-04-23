"""Config Flow for JLR InControl."""

import logging
from typing import Any
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
    UnitOfPressure,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult

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
    UNIQUE_ID,
)

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_USE_CHINA_SERVERS, default=False): bool,
    }
)

#        vol.Required(CONF_PIN, default="0000"): str,


@callback
def configured_instances(hass: HomeAssistant):
    """Return a set of configured JLR InControl instances."""
    return {entry.title for entry in hass.config_entries.async_entries(DOMAIN)}


async def validate_input(hass: HomeAssistant, data):
    """Validate the user input allows us to connect."""
    # TODO: match exceptions with aiojlrpy
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
        "vehicles": connection.vehicles,
    }


async def async_get_vehicle_name(hass: HomeAssistant, vehicle: jlrpy.Vehicle) -> None:
    """Get vehicle attributes."""
    attributes = await hass.async_add_executor_job(vehicle.get_attributes)

    if attributes:
        return attributes.get("nickname", vehicle.vin)
    return vehicle.vin


@config_entries.HANDLERS.register(DOMAIN)
class JLRInControlFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handles config setup."""

    VERSION = 2
    MINOR_VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self) -> None:
        """Initialize the jlrincontrol flow."""
        self.conf = {}
        self.options = {}
        self.info = None
        self.vehicles = []
        self.config_entry: config_entries.ConfigEntry | None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return JLRInControlOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input: dict[str, Any] = None) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if self._username_already_configured(user_input):
                return self.async_abort(reason="already_configured")

            try:
                self.info = await validate_input(self.hass, user_input)
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
                await self.async_set_unique_id(self.info[UNIQUE_ID])
                self._abort_if_unique_id_configured()

                # Add fixed device id
                user_input[CONF_DEVICE_ID] = str(uuid.uuid4())
                self.conf = user_input
                self.conf[CONF_PIN] = {}

                for vehicle in self.info.get("vehicles"):
                    name = await async_get_vehicle_name(self.hass, vehicle)
                    self.vehicles.append({"vin": vehicle.vin, "name": name})

                return await self.async_step_pin()

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors, last_step=False
        )

    async def async_step_pin(self, user_input: dict[str, Any] = None) -> FlowResult:
        """Set pin for vehicles on account."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self.conf[CONF_PIN].update(
                {self.vehicles[0].get("vin"): user_input[CONF_PIN]}
            )
            self.vehicles.pop(0)

            if not self.vehicles:
                return self.async_create_entry(title=self.info["title"], data=self.conf)
            return await self.async_step_pin()
        else:
            return self.async_show_form(
                step_id="pin",
                data_schema=vol.Schema({vol.Required(CONF_PIN, default="0000"): str}),
                errors=errors,
                description_placeholders={"name": self.vehicles[0].get("name")},
                last_step=len(self.vehicles) == 1,
            )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] = None
    ) -> FlowResult:
        """Handle a reconfiguration flow initialized by the user."""
        self.config_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        errors: dict[str, str] = {}

        RECONFIG_DATA_SCHEMA = vol.Schema(
            {
                vol.Required(
                    CONF_PASSWORD, default=self.config_entry.data[CONF_PASSWORD]
                ): str,
                vol.Required(
                    CONF_USE_CHINA_SERVERS,
                    default=self.config_entry.data[CONF_USE_CHINA_SERVERS],
                ): bool,
            }
        )

        if user_input is not None:
            try:
                user_input[CONF_USERNAME] = self.config_entry.data[CONF_USERNAME]
                self.info = await validate_input(self.hass, user_input)
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
                self.conf = user_input
                self.conf[CONF_PIN] = {}

                for vehicle in self.info.get("vehicles"):
                    name = await async_get_vehicle_name(self.hass, vehicle)
                    self.vehicles.append({"vin": vehicle.vin, "name": name})

                return await self.async_step_reconfigure_pin()

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=RECONFIG_DATA_SCHEMA,
            errors=errors,
            last_step=False,
            description_placeholders={"email": self.config_entry.data[CONF_USERNAME]},
        )

    async def async_step_reconfigure_pin(
        self, user_input: dict[str, Any] = None
    ) -> FlowResult:
        """Set pin for vehicles on account."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self.conf[CONF_PIN].update(
                {self.vehicles[0].get("vin"): user_input[CONF_PIN]}
            )
            self.vehicles.pop(0)

            if not self.vehicles:
                return self.async_update_reload_and_abort(
                    self.config_entry,
                    unique_id=self.info[UNIQUE_ID],
                    data={**self.config_entry.data, **self.conf},
                    reason="reconfigure_successful",
                )
            return await self.async_step_reconfigure_pin()
        else:
            return self.async_show_form(
                step_id="reconfigure_pin",
                data_schema=vol.Schema(
                    {
                        vol.Required(
                            CONF_PIN,
                            default=self.config_entry.data[CONF_PIN].get(
                                self.vehicles[0].get("vin"), "0000"
                            )
                            if isinstance(self.config_entry.data[CONF_PIN], dict)
                            else self.config_entry.data[CONF_PIN],
                        ): str
                    }
                ),
                errors=errors,
                description_placeholders={"name": self.vehicles[0].get("name")},
                last_step=len(self.vehicles) == 1,
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
    """Handles JLRIncontrol options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize JLRIncontrol options flow."""
        self.config_entry = config_entry
        self.options = dict(config_entry.options)

    async def async_step_init(self, user_input=None):
        """Handle options flow."""
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            options = self.config_entry.options | user_input
            return self.async_create_entry(title="", data=options)

        data_schema = vol.Schema(
            {
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
                    default=self.options.get(CONF_PRESSURE_UNIT, "Default"),
                ): vol.In(["Default", UnitOfPressure.BAR, UnitOfPressure.PSI]),
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
