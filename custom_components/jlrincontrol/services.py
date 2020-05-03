import inspect
import logging
import asyncio
from urllib import error
import time
from functools import partial

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class JLRService:
    def __init__(self, hass, vin):
        self.hass = hass
        self.data = hass.data[DOMAIN]
        self.vin = vin
        self.vehicle = self.data.vehicles[vin]
        self.service_code = None
        self.service_name = None
        self.attributes = self.vehicle.attributes
        self.nickname = self.attributes.get("nickname")

    async def async_call_service(self, **kwargs):
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
                            status = await self.hass.async_add_executor_job(
                                partial(service, **service_kwargs)
                            )
                            _LOGGER.debug(
                                "Service {} called on vehicle {}.  Awaiting feedback on success.".format(
                                    self.service_name, self.nickname,
                                )
                            )
                            # monitor service for success / failure
                            monitor_status = await self.async_monitor_service_call(
                                status.get("customerServiceId")
                            )

                            return monitor_status

                        except error.HTTPError as ex:
                            if ex.code == 401:
                                _LOGGER.warning(
                                    "Service: {} on vehicle {} - not authorised error. Is your pin correct?".format(
                                        self.service_name, self.nickname,
                                    )
                                )
                            else:
                                _LOGGER.debug(
                                    "Error calling service {} on vehicle {}.  Error is {}".format(
                                        self.service_name,
                                        self.nickname,
                                        ex.msg,
                                    )
                                )

                        except Exception as ex:
                            _LOGGER.debug(
                                "Error calling service {} on vehicle {}.  Error is {}".format(
                                    self.service_name, self.nickname, ex,
                                )
                            )
                    else:
                        _LOGGER.debug(
                            "Error calling service {} on vehicle {}. Another request is still processing. Please try again later.".format(
                                self.service_name, self.nickname,
                            )
                        )
                else:
                    _LOGGER.debug(
                        "Service {} is not available on vehicle {}".format(
                            self.service_name, self.nickname,
                        )
                    )
        else:
            _LOGGER.debug(
                "Error calling service {}.  Invalid parameters".format(
                    self.service_name
                )
            )

    def check_service_enabled(self, service_code):
        """Check service code is capable and enabled"""
        if service_code == "NA":
            return True
        else:
            for service in self.attributes.get("availableServices"):
                if service.get("serviceType") == service_code:
                    if service.get("vehicleCapable") and service.get(
                        "serviceEnabled"
                    ):
                        return True
        return False

    async def async_get_services(self):
        """Check for any exisitng queued service calls to vehicle"""
        services = await self.hass.async_add_executor_job(
            self.vehicle.get_services
        )
        if services:
            services = services.get("services")
            # Check if duplicate
            for service in services:
                service_id = service.replace(
                    "/vehicles/{}/services/".format(self.vin), ""
                )
                # Check service to see if matched to this service call
                # TODO: need to test for equivalents like RDL and RDU
                try:
                    status = await self.hass.async_add_executor_job(
                        partial(self.vehicle.get_service_status, service_id)
                    )
                    if status:
                        if status.get("serviceType") == self.service_code:
                            return True
                except:
                    pass

                return False

        else:
            return False

    async def async_check_service_status(self, service_id):
        """Get status of current service call"""
        return await self.hass.async_add_executor_job(
            self.vehicle.get_service_status, service_id
        )

    async def async_monitor_service_call(self, service_id):
        result = await self.async_check_service_status(service_id)

        if result:
            status = result.get("status")
            while status == "Started":
                _LOGGER.debug(
                    "Checking for {} service call result status.".format(
                        self.service_name
                    )
                )
                await asyncio.sleep(5)
                result = await self.async_check_service_status(service_id)
                status = result.get("status")
            if status and status == "Successful":
                _LOGGER.debug(
                    "Service call ({}) to vehicle {} was successful".format(
                        self.service_name, self.nickname
                    )
                )
                return status
            else:
                _LOGGER.debug(
                    "InControl service call ({}) to vehicle {} failed due to {}. \r\nFull return is {}".format(
                        self.service_name,
                        self.nickname,
                        result.get("failureReason"),
                        result,
                    )
                )
            return status
        else:
            return None
