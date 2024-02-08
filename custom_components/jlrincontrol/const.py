"""Integration constants."""
import logging

from homeassistant.const import (
    UnitOfEnergy,
    UnitOfLength,
    UnitOfTemperature,
    UnitOfVolume,
)

_LOGGER = logging.getLogger(__name__)

DOMAIN = "jlrincontrol"
DATA_JLR_CONFIG = "jlrincontrol_config"
JLR_DATA = "jlr_data"
VERSION = "3.0.0"

UNIQUE_ID = "unique_id"
DEVICE_ID = "device_id"

CONF_USE_CHINA_SERVERS = "use_china_servers"
CONF_DEVICE_ID = "device_id"
CONF_DISTANCE_UNIT = "distance_unit"
CONF_PRESSURE_UNIT = "pressure_unit"
CONF_ALL_DATA_SENSOR = "all_data_sensor"
CONF_DEBUG_DATA = "debug_data"
CONF_HEALTH_UPDATE_INTERVAL = "health_update_interval"
CONF_DEFAULT_CLIMATE_TEMP = "default_climate_temp"
CONF_DEFAULT_SERVICE_DURATION = "default_service_duration"

DEFAULT_SCAN_INTERVAL = 5
MIN_SCAN_INTERVAL = 1
DEFAULT_HEATH_UPDATE_INTERVAL = 0  # Default disabled

HEALTH_UPDATE_TRACKER = "health_update_tracker"
HEALTH_UPDATE_LISTENER = "health_update_listener"
UPDATE_LISTENER = "update_listener"

PLATFORMS = ["sensor", "lock", "device_tracker", "button", "switch"]

ATTR_PIN = "pin"
ATTR_EXPIRY = "expiration_time"
ATTR_CHARGE_LEVEL = "max_charge_level"
ATTR_TARGET_VALUE = "target_value"
ATTR_TARGET_TEMP = "target_temp"
ATTR_DEPARTURE_DATETIME = "departure_datetime"


JLR_TO_HASS_UNITS = {
    "Miles": UnitOfLength.MILES,
    "Km": UnitOfLength.KILOMETERS,
    "Litres": UnitOfVolume.LITERS,
    "USGallons": UnitOfVolume.GALLONS,
    "UKGallons": UnitOfVolume.GALLONS,
    "Celcius": UnitOfTemperature.CELSIUS,
    "Fahrenheit": UnitOfTemperature.FAHRENHEIT,
    "kWh": UnitOfEnergy.KILO_WATT_HOUR,
    "Wh": UnitOfEnergy.WATT_HOUR,
    "kWhPer100Dist": UnitOfEnergy.KILO_WATT_HOUR,
    "DistPerkWh": UnitOfLength.KILOMETERS,
    "WhPerDist": UnitOfEnergy.WATT_HOUR,
}

FUEL_TYPE_BATTERY = "Electric"
FUEL_TYPE_ICE = "ICE"
FUEL_TYPE_HYBRID = "Hybrid"
POWERTRAIN_PHEV = "PHEV"
POWERTRAIN_IC = "INTERNAL COMBUSTION"

SUBSCRIPTIONS = {
    "GBR025RC_L": "Pro Services",
    "GBR011BE-E1E2_L": "Protect",
    "GBR011DA-E1E2_L": "Remote Premium",
    "GBR011AJ_L": "Secure Tracker Pro",
}


JLR_WAKEUP_TO_HA = {
    "RECEIVING_SCHEDULE_ACCEPTANCE_WINDOW": "Active",
    "SLEEPING": "Sleeping",
}

JLR_CHARGE_STATUS_TO_HA = {
    "FULLYCHARGED": "Fully Charged",
    "BULKCHARGED": "Bulk Charged",
    "CHARGING": "Charging",
    "WAITINGTOCHARGE": "Waiting to Charge",
    "INITIALIZATION": "Initialising",
    "NOTCONNECTED": "Not Connected",
    "PAUSED": "Paused",
    "FAULT": "Fault",
    "UNKNOWN": "Unknown",
    "No Message": "Not Charging",
}

JLR_CHARGE_METHOD_TO_HA = {
    "WIRED": "Wired",
    "NOTCONNECTED": "Not Connected",
    "DEFAULT": "Default",
    "UNKNOWN": "Unknown",
}

SENSOR_TYPES = {
    "lids": ["Doors", "opening", "mdi:car-door-lock"],
    "windows": ["Windows", "opening", "mdi:car-door"],
    "door_lock_state": ["Door lock state", "lock", "mdi:car-key"],
    "lights_parking": ["Parking lights", "light", "mdi:car-parking-lights"],
    "condition_based_services": [
        "Condition based services",
        "problem",
        "mdi:wrench",
    ],
    "check_control_messages": [
        "Control messages",
        "problem",
        "mdi:car-tire-alert",
    ],
}

SENSOR_TYPES_ELEC = {
    "charging_status": ["Charging status", "power", "mdi:ev-station"],
    "connection_status": ["Connection status", "plug", "mdi:car-electric"],
}

DATA_ATTRS_CAR_INFO = {
    "registration": "registrationNumber",
    "model year": "modelYear",
    "make": "vehicleBrand",
    "model": "vehicleType",
    "body": "bodyType",
    "colour": "exteriorColorName",
    "doors": "numberOfDoors",
    "seats": "seatsQuantity",
    "engine": "engineCode",
    "transmission": "gearboxCode",
    "fuel": "fuelType",
    "weight": "grossWeight",
}

DATA_ATTRS_CLIMATE = {
    "climate timer1 month": "CLIMATE_STATUS_TIMER1_MONTH",
    "climate timer1 day": "CLIMATE_STATUS_TIMER1_DAY",
    "climate timer1 hour": "CLIMATE_STATUS_TIMER1_HOUR",
    "climate timeer1 minute": "CLIMATE_STATUS_TIMER1_MINUTE",
    "climate timer2 month": "CLIMATE_STATUS_TIMER2_MONTH",
    "climate timer2 day": "CLIMATE_STATUS_TIMER2_DAY",
    "climate timer2 hour": "CLIMATE_STATUS_TIMER2_HOUR",
    "climate timer2 minute": "CLIMATE_STATUS_TIMER2_MINUTE",
    "climate remaining run time": "CLIMATE_STATUS_REMAINING_RUNTIME",
    "climate ffh remaining run time": "CLIMATE_STATUS_FFH_REMAINING_RUNTIME",
    "climate venting time": "CLIMATE_STATUS_VENTING_TIME",
    "climate timer active": "CLIMATE_STATUS_TIMER_ACTIVATION_STATUS",
}

DATA_ATTRS_DOOR_STATUS = {
    "front left": "DOOR_FRONT_LEFT_LOCK_STATUS",
    "front right": "DOOR_FRONT_RIGHT_LOCK_STATUS",
    "rear left": "DOOR_REAR_LEFT_LOCK_STATUS",
    "rear right": "DOOR_REAR_RIGHT_LOCK_STATUS",
    "bonnet": "DOOR_ENGINE_HOOD_LOCK_STATUS",
    "boot": "DOOR_BOOT_LOCK_STATUS",
}

DATA_ATTRS_DOOR_POSITION = {
    "front left": "DOOR_FRONT_LEFT_POSITION",
    "front right": "DOOR_FRONT_RIGHT_POSITION",
    "rear left": "DOOR_REAR_LEFT_POSITION",
    "rear right": "DOOR_REAR_RIGHT_POSITION",
    "bonnet": "DOOR_ENGINE_HOOD_POSITION",
    "boot": "DOOR_BOOT_POSITION",
}

DATA_ATTRS_SERVICE_STATUS = {
    "brake fluid": "BRAKE_FLUID_WARN",
    "coolant level": "ENG_COOLANT_LEVEL_WARN",
    "DPF": "EXT_PARTICULATE_FILTER_WARN",
    "engine blockage": "ENGINE_BLOCK",
    "exhaust fluid": "EXT_EXHAUST_FLUID_WARN",
    "oil level": "EXT_OIL_LEVEL_WARN",
    "washer fluid": "WASHER_FLUID_WARN",
}

DATA_ATTRS_SERVICE_INFO = {
    "distance to service": "EXT_KILOMETERS_TO_SERVICE",
    "exhaust fluid distance to service": "EXT_EXHAUST_FLUID_DISTANCE_TO_SERVICE_KM",
    "exhaust fluid fill": "EXT_EXHAUST_FLUID_VOLUME_REFILL_LITRESX10",
}

DATA_ATTRS_TYRE_STATUS = {
    "front left": "TYRE_STATUS_FRONT_LEFT",
    "front right": "TYRE_STATUS_FRONT_RIGHT",
    "rear left": "TYRE_STATUS_REAR_LEFT",
    "rear right": "TYRE_STATUS_REAR_RIGHT",
}

DATA_ATTRS_TYRE_PRESSURE = {
    "front left": "TYRE_PRESSURE_FRONT_LEFT",
    "front right": "TYRE_PRESSURE_FRONT_RIGHT",
    "rear left": "TYRE_PRESSURE_REAR_LEFT",
    "rear right": "TYRE_PRESSURE_REAR_RIGHT",
}

DATA_ATTRS_SECURITY = {
    "alarm": "THEFT_ALARM_STATUS",
    "panic alarm": "IS_PANIC_ALARM_TRIGGERED",
}

DATA_ATTRS_SAFETY = {}

DATA_ATTRS_WINDOW_STATUS = {
    "front left": "WINDOW_FRONT_LEFT_STATUS",
    "front right": "WINDOW_FRONT_RIGHT_STATUS",
    "rear left": "WINDOW_REAR_LEFT_STATUS",
    "rear right": "WINDOW_REAR_RIGHT_STATUS",
    "sunroof": "IS_SUNROOF_OPEN",
}

SERVICE_STATUS_OK = ["CLEAR", "FUNCTIONING", "NORMAL", "NORMAL_UNBLOCKED"]

DEPRECATED_SERVICES = {
    "update_health_status": {
        "use_instead_service": "button.press",
        "use_instead_entity": "Update From Vehicle",
    },
    "lock_vehicle": {
        "use_instead_service": "lock.lock",
        "use_instead_entity": "Doors",
    },
    "unlock_vehicle": {
        "use_instead_service": "lock.unlock",
        "use_instead_entity": "Doors",
    },
    "reset_alarm": {
        "use_instead_service": "button.press",
        "use_instead_entity": "Reset Alarm",
    },
    "honk_blink": {
        "use_instead_service": "button.press",
        "use_instead_entity": "Honk Blink",
    },
    "start_vehicle": {
        "use_instead_service": "switch.turn_on",
        "use_instead_entity": "Climate (Engine)",
    },
    "stop_vehicle": {
        "use_instead_service": "switch.turn_off",
        "use_instead_entity": "Climate (Engine)",
    },
    "start_charging": {
        "use_instead_service": "switch.turn_on",
        "use_instead_entity": "Charging",
    },
    "stop_charging": {
        "use_instead_service": "switch.turn_off",
        "use_instead_entity": "Charging",
    },
    "start_preconditioning": {
        "use_instead_service": "switch.turn_on",
        "use_instead_entity": "Climate (Electric)",
    },
    "stop_preconditioning": {
        "use_instead_service": "switch.turn_off",
        "use_instead_entity": "Climate (Electric)",
    },
}

SUPPORTED_BUTTON_SERVICES = {
    "ALOFF": {
        "name": "Reset Alarm",
        "service": "reset_alarm",
        "icon": "mdi:alarm-light-off",
    },
    "HBLF": {
        "name": "Honk Blink",
        "service": "honk_blink",
        "icon": "mdi:car-light-high",
    },
    "VHS": {
        "name": "Update From Vehicle",
        "service": "update_health_status",
        "icon": "mdi:update",
    },
}

SUPPORTED_SWITCH_SERVICES = {
    "CP": {
        "name": "Charging",
        "on_service": "start_charging",
        "off_service": "stop_charging",
        "params": ["pin"],
        "icon": "mdi:car-electric",
        "state": "is_charging",
    },
    "ECC": {
        "name": "Climate (Electric)",
        "on_service": "start_preconditioning",
        "off_service": "stop_preconditioning",
        "params": ["pin"],
        "icon": "mdi:air-conditioner",
        "add_on_params": ["target_temp"],
        "state": "climate_electric_active",
    },
    "GMCC": {
        "name": "Guardian Mode",
        "on_service": "enable_guardian_mode",
        "off_service": "disable_guardian_mode",
        "params": ["pin"],
        "icon": "mdi:shield-car",
        "add_on_params": ["expiration_time"],
        "state": "guardian_mode_active",
        "attrs": {"expires": "guardian_mode.expiry"},
    },
    "PM": {
        "name": "Journey Recording",
        "on_service": "disable_privacy_mode",
        "off_service": "enable_privacy_mode",
        "params": ["pin"],
        "icon": "mdi:transit-connection-variant",
        "state": "privacy_mode_enabled",
    },
    "REON": {
        "name": "Climate (Engine)",
        "on_service": "start_vehicle",
        "off_service": "stop_vehicle",
        "params": ["pin"],
        "icon": "mdi:air-conditioner",
        "add_on_params": ["target_value"],
        "state": "climate_engine_active",
    },
    "SM": {
        "name": "Service Mode",
        "on_service": "enable_service_mode",
        "off_service": "disable_service_mode",
        "params": ["pin", "expiration_time"],
        "icon": "mdi:car-wrench",
        "state": "service_mode_enabled",
    },
    "TM": {
        "name": "Transport Mode",
        "on_service": "enable_transport_mode",
        "off_service": "disable_transport_mode",
        "params": ["pin", "expiration_time"],
        "icon": "mdi:train-car-flatbed-car",
        "state": "transport_mode_enabled",
    },
}

JLR_SERVICES = {
    "update_health_status": {
        "custom_service": True,
        "function_name": "get_health_status",
        "service_code": "VHS",
        "schema": [],
    },
    "lock_vehicle": {
        "custom_service": True,
        "function_name": "lock",
        "service_code": "RDL",
        "schema": ["SERVICES_BASE_SCHEMA", "SERVICES_PIN_SCHEMA"],
    },
    "unlock_vehicle": {
        "custom_service": True,
        "function_name": "unlock",
        "service_code": "RDU",
        "schema": ["SERVICES_BASE_SCHEMA", "SERVICES_PIN_SCHEMA"],
    },
    "reset_alarm": {
        "custom_service": True,
        "function_name": "reset_alarm",
        "service_code": "ALOFF",
        "schema": ["SERVICES_BASE_SCHEMA", "SERVICES_PIN_SCHEMA"],
    },
    "honk_blink": {
        "custom_service": True,
        "function_name": "honk_blink",
        "service_code": "HBLF",
        "schema": ["SERVICES_BASE_SCHEMA"],
    },
    "start_vehicle": {
        "custom_service": True,
        "function_name": "remote_engine_start",
        "service_code": "REON",
        "schema": [
            "SERVICES_BASE_SCHEMA",
            "SERVICES_PIN_SCHEMA",
            "SERVICES_TARGET_VALUE_SCHEMA",
        ],
    },
    "stop_vehicle": {
        "custom_service": True,
        "function_name": "remote_engine_stop",
        "service_code": "REOFF",
        "schema": ["SERVICES_BASE_SCHEMA", "SERVICES_PIN_SCHEMA"],
    },
    "start_charging": {
        "custom_service": True,
        "function_name": "charging_start",
        "service_code": "CP",
        "schema": ["SERVICES_BASE_SCHEMA"],
    },
    "stop_charging": {
        "custom_service": True,
        "function_name": "charging_stop",
        "service_code": "CP",
        "schema": ["SERVICES_BASE_SCHEMA"],
    },
    "set_departure_timer": {
        "custom_service": True,
        "function_name": "add_departure_timer",
        "service_code": "CP",
        "schema": ["SERVICES_BASE_SCHEMA", "SERVICES_DEPARTURE_TIME_SCHEMA"],
    },
    "delete_departure_timer": {
        "custom_service": True,
        "function_name": "delete_departure_timer",
        "service_code": "CP",
        "schema": ["SERVICES_BASE_SCHEMA"],
    },
    "start_preconditioning": {
        "custom_service": True,
        "function_name": "preconditioning_start",
        "service_code": "ECC",
        "schema": ["SERVICES_BASE_SCHEMA", "SERVICES_TARGET_TEMP_SCHEMA"],
    },
    "stop_preconditioning": {
        "custom_service": True,
        "function_name": "preconditioning_stop",
        "service_code": "ECC",
        "schema": ["SERVICES_BASE_SCHEMA"],
    },
    "set_max_charge_level": {
        "custom_service": True,
        "function_name": "set_max_soc",
        "service_code": "CP",
        "schema": ["SERVICES_BASE_SCHEMA", "SERVICES_CHARGE_LEVEL_SCHEMA"],
    },
    "set_one_off_max_charge_level": {
        "custom_service": True,
        "function_name": "set_one_off_max_soc",
        "service_code": "CP",
        "schema": ["SERVICES_BASE_SCHEMA", "SERVICES_CHARGE_LEVEL_SCHEMA"],
    },
    "enable_privacy_mode": {
        "custom_service": False,
        "function_name": "enable_privacy_mode",
        "service_code": "PM",
        "schema": ["SERVICES_BASE_SCHEMA"],
    },
    "disable_privacy_mode": {
        "custom_service": False,
        "function_name": "disable_privacy_mode",
        "service_code": "PM",
        "schema": ["SERVICES_BASE_SCHEMA"],
    },
    "enable_guardian_mode": {
        "custom_service": True,
        "function_name": "enable_guardian_mode",
        "service_code": "GMCC",
        "schema": [
            "SERVICES_BASE_SCHEMA",
            "SERVICES_PIN_SCHEMA",
            "SERVICES_EXPIRY_SCHEMA",
        ],
    },
    "disable_guardian_mode": {
        "custom_service": True,
        "function_name": "disable_guardian_mode",
        "service_code": "GMCC",
        "schema": ["SERVICES_BASE_SCHEMA", "SERVICES_PIN_SCHEMA"],
    },
    "enable_service_mode": {
        "custom_service": True,
        "function_name": "enable_service_mode",
        "service_code": "SM",
        "schema": [
            "SERVICES_BASE_SCHEMA",
            "SERVICES_PIN_SCHEMA",
            "SERVICES_EXPIRY_SCHEMA",
        ],
    },
    "disable_service_mode": {
        "custom_service": True,
        "function_name": "disable_service_mode",
        "service_code": "SM",
        "schema": ["SERVICES_BASE_SCHEMA", "SERVICES_PIN_SCHEMA"],
    },
    "enable_transport_mode": {
        "custom_service": True,
        "function_name": "enable_transport_mode",
        "service_code": "TM",
        "schema": [
            "SERVICES_BASE_SCHEMA",
            "SERVICES_PIN_SCHEMA",
            "SERVICES_EXPIRY_SCHEMA",
        ],
    },
    "disable_transport_mode": {
        "custom_service": True,
        "function_name": "disable_transport_mode",
        "service_code": "TM",
        "schema": ["SERVICES_BASE_SCHEMA", "SERVICES_PIN_SCHEMA"],
    },
}
