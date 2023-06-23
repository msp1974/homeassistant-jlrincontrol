"""Diagnostics support for Wiser"""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntry

# from aioWiserHeatAPI.cli import anonymise_data

from .const import DOMAIN, JLR_DATA


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

    diag_data["User"] = data.user.__dict__
    for vehicle in data.vehicles:
        diag_data[vehicle] = data.vehicles[vehicle].__dict__
    # TODO: Redact sensitive info
    return diag_data
