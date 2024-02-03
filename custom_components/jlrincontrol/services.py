"""Manage execution of services."""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from functools import partial
import inspect
import logging
from urllib.error import HTTPError

from .const import JLR_SERVICES
from .util import convert_datetime_to_epoch, convert_temp_value, field_mask

_LOGGER = logging.getLogger(__name__)


@dataclass
class StatusInfo:
    """Holds process status info."""

    status: str
    timestamp: datetime
    start_time: datetime
    service_code: str
    failure_description: str
    service_id: str
    vin: str
    active: bool
    initiator: str
    event_trigger: str


class JLRService:
    """Handles service call."""

    def __init__(
        self,
        coordinator,
        vin: str,
        service: str,
    ) -> None:
        """Initialise."""
        self.hass = coordinator.hass
        self.coordinator = coordinator
        self.vin = vin
        self.vehicle = self.coordinator.vehicles[vin]
        self.service_code = JLR_SERVICES[service].get("service_code")
        self.service_name = JLR_SERVICES[service].get("function_name")

    def check_service_supported(self, service_code) -> bool:
        """Check service code is capable and enabled."""
        if service_code == "NA":
            return True
        if service_code in self.vehicle.supported_services:
            return True
        return False

    async def is_service_call_in_progress(self) -> bool:
        """Check if a service call is already in progress."""
        services = await self.hass.async_add_executor_job(self.vehicle.api.get_services)
        if services:
            return True
        return False

    async def async_get_service_status(self, service_id) -> str:
        """Get status of current service call."""
        return await self.hass.async_add_executor_job(
            self.vehicle.api.get_service_status, service_id
        )

    async def validate_service_call(self):
        """Validate service supported."""
        if self.service_code and self.service_name:
            # Check this is a supported service on this vehicle
            if self.check_service_supported(self.service_code):
                # Check no other service calls are awaiting
                if not await self.is_service_call_in_progress():
                    # OK to make service call
                    return True
                else:
                    _LOGGER.error(
                        "Error calling service %s on vehicle %s. %s",
                        self.service_name,
                        self.vehicle.name,
                        "Another request is still processing",
                    )
            else:
                _LOGGER.error(
                    "Service %s is not available on vehicle %s",
                    self.service_name,
                    self.vehicle.name,
                )
        else:
            _LOGGER.error(
                "Error calling service %s.  Invalid parameters",
                self.service_name,
            )
        return False

    async def async_call_service(self, **kwargs) -> bool:
        """Call jlr service."""
        if await self.validate_service_call():
            service_kwargs = {}

            _LOGGER.debug("Service called with params - %s", kwargs)

            # populate required parameters for service call
            service = getattr(self.vehicle.api, self.service_name)
            for param in inspect.signature(service).parameters:
                if param in ["target_value", "target_temp"]:
                    # convert temp values to car requirements
                    service_kwargs[param] = convert_temp_value(
                        self.hass.config.units.temperature_unit,
                        self.service_code,
                        kwargs.get(param),
                    )
                elif param in ["expiration_time"]:
                    # convert datetime string to epoc time
                    service_kwargs[param] = convert_datetime_to_epoch(kwargs.get(param))
                else:
                    service_kwargs[param] = kwargs.get(param)

            # Call service
            try:
                status = await self.hass.async_add_executor_job(
                    partial(service, **service_kwargs)
                )
                _LOGGER.debug(
                    "Service %s called on vehicle %s. %s",
                    self.service_name,
                    self.vehicle.name,
                    "Awaiting feedback on success.",
                )
                _LOGGER.debug("Service call response: %s", status)
                # monitor service for success / failure
                if not status:
                    return True
                if status.get("error"):
                    return False
                success = await self.async_monitor_service_call(
                    status.get("customerServiceId")
                )

                return success

            except HTTPError as ex:
                if ex.code == 401:
                    _LOGGER.warning(
                        "Unauthorised error calling %s on vehicle %s",
                        self.service_name,
                        self.vehicle.name,
                    )
                else:
                    _LOGGER.error(
                        "Error calling service %s on vehicle %s. Error is %s",
                        self.service_name,
                        self.vehicle.name,
                        ex.msg,
                    )

        else:
            _LOGGER.error(
                "Error calling service %s.  Invalid parameters",
                self.service_name,
            )
        return False

    async def async_monitor_service_call(self, service_id):
        """Monitor service call for result."""
        service_status = await self.async_get_service_status(service_id)
        status = service_status.get("status", "Unknown")

        if status:
            while status in ["Started", "Running"]:
                _LOGGER.debug(
                    "Checking for %s call result status.  Currently %s. %s",
                    self.service_name,
                    status,
                    service_status,
                )
                await asyncio.sleep(2)
                service_status = await self.async_get_service_status(service_id)
                status = service_status.get("status", "Unknown")

            if status and status in ["Successful", "MessageDelivered"]:
                _LOGGER.debug(
                    "Service call (%s) to vehicle %s was successful",
                    self.service_name,
                    self.vehicle.name,
                )
                return True
            else:
                # Anonymise data in log output
                service_status["vehicleId"] = field_mask(service_status["vehicleId"], 3, 2)
                service_status["customerServiceId"] = field_mask(
                    service_status["customerServiceId"], 11, 9
                )

                _LOGGER.error(
                    "JLR InControl service call %s to vehicle %s failed. %s",
                    self.service_name,
                    self.vehicle.name,
                    service_status.get("failureReason"),
                )

                _LOGGER.debug("Full status return is %s", service_status)
                return False
        else:
            return False
