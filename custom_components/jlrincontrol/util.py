"""Utility functions."""
from datetime import datetime
import logging
from os.path import exists
from typing import Any

import aiofiles
from aiojlrpy import Alert

from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)


def get_alert_by_name(vehicle, alert_name: str) -> Alert | None:
    """Get vehicle alert by name."""
    alerts = [alert for alert in vehicle.status.alerts if alert.name == alert_name]
    if alerts:
        return alerts[0]


def field_mask(str_value, from_start=0, from_end=0):
    """Redact sensitive field data."""
    str_mask = "x" * (len(str_value) - from_start - from_end)
    return f"{str_value[:from_start]}{str_mask}{str_value[-from_end:]}"


def requires_pin(service_type, service_code):
    """Return if service requires pin."""
    if "pin" in service_type[service_code].get("params", {}):
        return True
    return False


def get_value_match(data: dict, key: str, value: str) -> bool:
    """Get if attribute matches value."""
    return True if data.get(key) == value else False


def get_is_date_active(data: dict, key: str) -> bool:
    """Get if attribute as datetime before now."""
    try:
        attr_dt = dt_util.as_utc(dt_util.parse_datetime(data.get(key)))
        if attr_dt < dt_util.utcnow():
            return False
        return True
    except (ValueError, TypeError):
        return False


def convert_temp_value(temp_unit, service_code, target_value):
    """Convert from C/F to value between 31-57 (31 is LO 57 is HOT) needed for service call."""

    # Handle setting car units (prior to version 2.0)
    if target_value >= 31 and target_value <= 57:
        return target_value

    # Engine start/set rcc value
    if service_code == "REON":
        # Get temp units
        if temp_unit == UnitOfTemperature.CELSIUS:
            # Convert from C
            return min(57, max(31, int(target_value * 2)))
        else:
            # Convert from F
            return min(57, max(31, target_value - 27))

    # Climate preconditioning
    if service_code == "ECC":
        if temp_unit == UnitOfTemperature.CELSIUS:
            return min(285, max(155, int(target_value * 10)))
        else:
            # Convert from F
            return min(285, max(155, int(((target_value - 27) / 2) * 10)))


def convert_datetime_to_epoch(dt: str) -> int:
    """Convert string datetime to epoch time."""
    utc_time = datetime.strptime(dt, "%Y-%m-%d %H:%M:%S")
    epoch_time = (utc_time - datetime(1970, 1, 1)).total_seconds()
    return round(epoch_time * 1000)


def to_local_datetime(dte: str):
    """Convert to local time."""
    try:
        return dt_util.as_local(dt_util.parse_datetime(dte))
    except (ValueError, TypeError):
        return None


def split_datetime(dte: datetime) -> dict:
    """Split a datetime value into component parts and return dict."""
    output = {}
    output["year"] = dte.year
    output["month"] = dte.month
    output["day"] = dte.day
    output["hour"] = dte.hour
    output["minute"] = dte.minute
    return output


def get_attribute(obj, path: str) -> Any | None:
    """Get attribute from dotted notation."""
    attrs = path.split(".")
    temp = obj
    for attr in attrs:
        if hasattr(temp, attr):
            temp = getattr(temp, attr)
        else:
            return None
    return temp


async def save_user_prefs(hass: HomeAssistant, user_id, uoms) -> bool:
    """Write user preferences to file."""
    file = f"{hass.config.config_dir}/.storage/jlrincontrol_data_{user_id}"
    # Write to config file
    async with aiofiles.open(file, mode="w") as config_file:
        # try:
        await config_file.write(uoms)
    return True


async def get_user_prefs(hass: HomeAssistant, user_id) -> dict:
    """Get user prefs from file."""
    file = f"{hass.config.config_dir}/.storage/jlrincontrol_data_{user_id}"
    if exists(file):
        async with aiofiles.open(file, mode="r") as user_pref_file:
            contents = await user_pref_file.read()
            if contents:
                uoms = contents
        return uoms


def debug_log_status(status):
    """Output status to debug log."""
    for status_class in ["core", "ev", "alerts"]:
        if getattr(status, status_class):
            _LOGGER.debug(
                "STATUS - %s: %s",
                status_class.upper(),
                getattr(status, status_class),
            )
