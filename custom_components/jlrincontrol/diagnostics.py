"""Diagnostics support for JLRInControl."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import datetime
import logging
from typing import Any

from aiojlrpy import VehicleStatus

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntry

from .const import DOMAIN, JLR_DATA
from .vehicle import JLRVehicle

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


@dataclass
class VehicleDiagnosticData:
    """Hold vehicle data."""

    vin: str
    name: str = ""
    engine_type: str = "Unknown"
    fuel: str = "Unknown"
    last_updated: datetime = None
    position: dict = field(default_factory=dict)
    attributes: dict = field(default_factory=dict)
    supported_services: list = field(default_factory=list)
    status: VehicleStatus = field(default_factory=VehicleStatus)
    guardian_mode: dict = field(default_factory=dict)
    tracked_status: dict = field(default_factory=dict)
    last_trip: dict = field(default_factory=dict)
    trips: dict = field(default_factory=dict)
    target_climate_temp: int = 0


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
    # vehicle_data = copy.deepcopy(data.vehicles)
    for vehicle in data.vehicles:
        vehicle_data = get_diagnostic_data(data.vehicles[vehicle])
        diag_data[anonymise_vin(vehicle)] = anonymise_data(
            copy.deepcopy(vehicle_data.__dict__),
        )
    return diag_data


def get_diagnostic_data(data: JLRVehicle) -> VehicleDiagnosticData:
    """Return diag data."""
    return VehicleDiagnosticData(
        vin=data.vin,
        name=data.vin,
        engine_type=data.engine_type,
        fuel=data.fuel,
        last_updated=data.last_updated,
        position=data.position,
        attributes=data.attributes,
        supported_services=data.supported_services,
        status=data.status,
        guardian_mode=data.guardian_mode,
        tracked_status=data.tracked_status,
        last_trip=data.last_trip,
        trips=data.trips,
        target_climate_temp=data.target_climate_temp,
    )


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
