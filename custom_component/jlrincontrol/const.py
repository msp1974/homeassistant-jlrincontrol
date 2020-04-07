import logging

_LOGGER = logging.getLogger(__name__)

DOMAIN = "jaguarlandrover"
DATA_JLR_CONFIG = "jlr_config"
VERSION = "0.1.0"
JLR_PLATFORMS = ["sensor", "switch"]


JLR_SERVICES = {
    "SERVICE_BOOST_HEATING": "boost_heating",
    "SERVICE_COPY_SCHEDULE": "copy_schedule",
    "SERVICE_GET_SCHEDULE": "get_schedule",
    "SERVICE_SET_SCHEDULE": "set_schedule",
    "SERVICE_SET_SMARTPLUG_MODE": "set_smartplug_mode",
    "SERVICE_SET_HOTWATER_MODE": "set_hotwater_mode",
}
