"""Diagnostics support for JLRInControl."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntry

from .const import DOMAIN, JLR_DATA

_LOGGER = logging.getLogger(__name__)

ANON_KEYS = [
    "vin",
    "longitude",
    "latitude",
    "minLongitude",
    "minLatitude",
    "maxLongitude",
    "maxLatitude",
    "address",
    "postalCode",
    "city",
    "registrationNumber",
    "serialNumber",
    "TU_STATUS_IMEI",
]


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    return _async_get_diagnostics(hass, entry)


@callback
def _async_get_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
    device: DeviceEntry | None = None,
) -> dict[str, Any]:
    data = hass.data[DOMAIN][entry.entry_id][JLR_DATA]

    diag_data = {}

    diag_data["Device"] = device

    diag_data["User"] = data.user.__dict__
    for vehicle in data.vehicles.copy():
        diag_data[anonymise_vin(vehicle)] = anonymise_data(
            data.vehicles[vehicle].__dict__
        )
    return diag_data


def anonymise_data(data: dict) -> dict:
    """Anonymise sensitive data."""
    for key, value in data.items():
        if isinstance(value, dict):
            data[key] = anonymise_data(value)
        elif key in ANON_KEYS:
            data[key] = "**REDACTED**"
    return data


def anonymise_vin(vin) -> str:
    """Anonymise vin number."""
    return vin[:11] + "XXXXXX"
