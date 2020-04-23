import inspect
import logging
import asyncio
from urllib import error
import time

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class JLRService:
    def __init__(self, hass, vehicle):
        self._hass = hass
        self.data = hass.data[DOMAIN]
        self.vehicle = vehicle
        self.service_code = None
        self.service_name = None
        self.attributes = self.vehicle.attributes

    async def async_call_service(self, **kwargs):
        # TODO: Validate entity
        self.service_code = kwargs.get("service_code")
        self.service_name = kwargs.get("service_name")

        if self.service_code and self.service_name:
            # Check this is a valid service
            if kwargs.get("service_name"):
                if self.check_service_enabled(self.service_code):

                    # Check no other service calls are awaiting
                    if not await self.async_get_services():
                        service_kwargs = {}

                        # populate required parameters for service call
                        service = getattr(self.vehicle, self.service_name)
                        for param in inspect.signature(service).parameters:
                            service_kwargs[param] = kwargs.get(param)

                        # Call service
                        try:
                            status = service(**service_kwargs)
                            _LOGGER.debug(
                                "Service {} called.  Awaiting feedback on success.".format(
                                    self.service_name
                                )
                            )
                            # monitor service for success / failure
                            monitor_status = await self.async_monitor_service_call(
                                status.get("customerServiceId")
                            )

                            # Call update on return of monitor
                            await self.data.async_update()
                            return monitor_status

                        except error.HTTPError as ex:
                            if ex.code == 401:
                                _LOGGER.warning(
                                    "Service: {} - not authorised error. Is your pin correct?".format(
                                        self.service_name
                                    )
                                )
                            else:
                                _LOGGER.debug(
                                    "Error calling service {}.  Error is {}".format(
                                        self.service_name, ex.msg
                                    )
                                )

                        except Exception as ex:
                            _LOGGER.debug(
                                "Error calling service {}.  Error is {}".format(
                                    ex, self.service_name
                                )
                            )

                        # log in debug for success. log in warn for failure
                    else:
                        # TODO: State the service that is being waited for from service status code
                        _LOGGER.warning(
                            "Another service request is still processing. Please try again later."
                        )
                else:
                    _LOGGER.debug(
                        "Service {} is not available on this vehicle".format(
                            self.service_name
                        )
                    )
        else:
            _LOGGER.debug("Error calling service.  Invalid parameters")

    def check_service_enabled(self, service_code):
        """Check service code is capable and enabled"""
        if service_code == "NA":
            return True
        else:
            for service in self.attributes.get("availableServices"):
                if service.get("serviceType") == service_code:
                    if service.get("vehicleCapable") and service.get("serviceEnabled"):
                        return True
        return False

    async def async_get_services(self):
        """Check for any exisitng queued service calls to vehicle"""
        # TODO: make this return true or false if existing
        return await self._hass.async_add_executor_job(self.vehicle.get_services)

    async def async_check_service_status(self, service_id):
        """Get status of current service call"""
        return await self._hass.async_add_executor_job(
            self.vehicle.get_service_status, service_id
        )

    async def async_monitor_service_call(self, service_id):
        result = await self.async_check_service_status(service_id)

        if result:
            status = result.get("status")
            while status == "Started":
                _LOGGER.debug("Checking for service call result status.")
                await asyncio.sleep(5)
                result = await self.async_check_service_status(service_id)
                status = result.get("status")
            if status and status == "Successful":
                _LOGGER.debug("Service call successful")
                return status
            else:
                _LOGGER.warning(
                    "InControl service call failed due to {}. \r\nFull return is {}".format(
                        result.get("failureReason"), result
                    )
                )
            return status
        else:
            return None
