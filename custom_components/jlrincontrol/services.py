import inspect
import logging
import asyncio
from urllib import error
from functools import partial

from .const import DOMAIN, JLR_DATA
from .util import convert_temp_value, field_mask

_LOGGER = logging.getLogger(__name__)


class JLRService:
    def __init__(self, hass, config_entry, vin):
        self.hass = hass
        self.data = hass.data[DOMAIN][config_entry.entry_id][JLR_DATA]
        self.vin = vin
        self.vehicle = self.data.vehicles[vin]
        self.service_code = None
        self.service_name = None
        self.attributes = self.vehicle.attributes
        self.nickname = self.attributes.get("nickname")

    async def validate_service_call(self):
        if self.service_code and self.service_name:
            # Check this is a valid service
            if self.check_service_enabled(self.service_code):
                # Check no other service calls are awaiting
                if not await self.async_get_services():
                    # OK to make service call
                    return True
                else:
                    _LOGGER.error(
                        "Error calling service {} on vehicle {}. ".format(
                            self.service_name,
                            self.nickname,
                        )
                        + "Another request is still processing. "
                        + "Please try again later."
                    )
            else:
                _LOGGER.error(
                    "Service {} is not available on vehicle {}".format(
                        self.service_name,
                        self.nickname,
                    )
                )
        else:
            _LOGGER.error(
                "Error calling service {}.  Invalid parameters".format(
                    self.service_name
                )
            )
        return False

    async def async_call_service(self, **kwargs):
        self.service_code = kwargs.get("service_code")
        self.service_name = kwargs.get("service_name")

        if await self.validate_service_call():
            service_kwargs = {}

            # populate required parameters for service call
            service = getattr(self.vehicle, self.service_name)
            for param in inspect.signature(service).parameters:
                if param in ["target_value", "target_temp"]:
                    # convert temp values to car requirements
                    service_kwargs[param] = convert_temp_value(
                        self.hass.config.units.temperature_unit,
                        self.service_code,
                        kwargs.get(param),
                    )
                else:
                    service_kwargs[param] = kwargs.get(param)

            # Call service
            try:
                status = await self.hass.async_add_executor_job(
                    partial(service, **service_kwargs)
                )
                _LOGGER.info(
                    "Service {} called on vehicle {}. ".format(
                        self.service_name,
                        self.nickname,
                    )
                    + "Awaiting feedback on success."
                )
                # monitor service for success / failure
                monitor_status = await self.async_monitor_service_call(
                    status.get("customerServiceId")
                )

                return monitor_status

            except error.HTTPError as ex:
                if ex.code == 401:
                    _LOGGER.warning(
                        "Service: {} on vehicle {} ".format(
                            self.service_name,
                            self.nickname,
                        )
                        + "- not authorised error. Is your pin correct?"
                    )
                else:
                    _LOGGER.error(
                        "Error calling service {} on vehicle {}. ".format(
                            self.service_name, self.nickname
                        )
                        + "Error is {}".format(ex.msg)
                    )

            except Exception as ex:
                _LOGGER.error(
                    "Error calling service {} on vehicle {}. ".format(
                        self.service_name, self.nickname
                    )
                    + "Error is {}".format(ex)
                )
        else:
            _LOGGER.error(
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
                except Exception:
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
            while status and status in ["Started", "Running"]:
                _LOGGER.info(
                    "Checking for {} service call result status.  Currently {}.".format(
                        self.service_name, status
                    )
                )
                await asyncio.sleep(5)
                result = await self.async_check_service_status(service_id)
                status = result.get("status")
            if status and status in ["Successful", "MessageDelivered"]:
                _LOGGER.info(
                    "Service call ({}) to vehicle {} was successful".format(
                        self.service_name, self.nickname
                    )
                )
                return "Successful"
            else:
                # Anonymise data in log output
                result["vehicleId"] = field_mask(result["vehicleId"], 3, 2)
                result["customerServiceId"] = field_mask(
                    result["customerServiceId"], 11, 9
                )

                _LOGGER.error(
                    "JLR InControl service call ({}) to vehicle {} ".format(
                        self.service_name,
                        self.nickname,
                    )
                    + "failed due to {}.".format(result.get("failureReason"))
                )

                _LOGGER.debug("Full status return is {}.".format(result))
            return status
        else:
            return None
