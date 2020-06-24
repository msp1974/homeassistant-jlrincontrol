import logging
from homeassistant.const import (
    ENERGY_KILO_WATT_HOUR,
    TEMP_CELSIUS,
    TEMP_FAHRENHEIT,
    LENGTH_KILOMETERS,
    LENGTH_MILES,
    VOLUME_LITERS,
    VOLUME_GALLONS,
)

_LOGGER = logging.getLogger(__name__)

DOMAIN = "jlrincontrol"
DATA_JLR_CONFIG = "jlrincontrol_config"
JLR_DATA = "jlr_data"
VERSION = "2.0.2"

DEFAULT_SCAN_INTERVAL = 5
MIN_SCAN_INTERVAL = 1
DEFAULT_HEATH_UPDATE_INTERVAL = 0  # Default disabled

SIGNAL_STATE_UPDATED = f"{DOMAIN}.updated"

# Conversions
KMS_TO_MILES = 0.62137

FUEL_TYPE_BATTERY = "Electric"

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

JLR_USER_PREF_PARAMS = [
    "distance",
    "volume",
    "temperature",
    "distPerVol",
    "energy",
    "energyPerDist",
]

JLR_TO_HA_UNITS = {
    "distance": {"Km": LENGTH_KILOMETERS, "Miles": LENGTH_MILES},
    "volume": {
        "Litre": VOLUME_LITERS,
        "UkGallons": VOLUME_GALLONS,
        "UsGallons": VOLUME_GALLONS,
    },
    "temperature": {"Celsius": TEMP_CELSIUS, "Fahrenheit": TEMP_FAHRENHEIT},
    "distPerVol": {"DistPerVol": "Km/L"},
    "energy": {"kWh": ENERGY_KILO_WATT_HOUR},
    "energyPerDist": {"kWhPer100Dist": ENERGY_KILO_WATT_HOUR + "/100m"},
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

DATA_ATTRS_EV_CHARGE_INFO = {
    "charging": "EV_IS_CHARGING",
    "charge level": "EV_STATE_OF_CHARGE",
    "charging method": "EV_CHARGING_METHOD",
    "charging mode": "EV_CHARGING_MODE_CHOICE",
    "charge rate": "EV_CHARGING_RATE_{}_PER_HOUR",
    "charge type": "EV_CHARGE_TYPE",
    "is plugged in": "EV_IS_PLUGGED_IN",
    "KWH used since last charge": "EV_ENERGY_CONSUMED_LAST_CHARGE_KWH",
    "minutes to full charge": "EV_MINUTES_TO_FULLY_CHARGED",
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
    "climate timer2 hour": "CLIMATE_STATUS_TIMER2_HOUR",
    "climate timer2 day": "CLIMATE_STATUS_TIMER2_DAY",
    "climate timer2 minute": "CLIMATE_STATUS_TIMER2_MINUTE",
    "climate remaining run time": "CLIMATE_STATUS_REMAINING_RUNTIME",
    "climate ffh remaining run time": "CLIMATE_STATUS_FFH_REMAINING_RUNTIME",
    "climate venting time": "CLIMATE_STATUS_VENTING_TIME",
    "climate timer active": "CLIMATE_STATUS_TIMER_ACTIVATION_STATUS",
    "climate status": "CLIMATE_STATUS_OPERATING_STATUS",
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

JLR_SERVICES = {
    "update_health_status": {
        "function_name": "get_health_status",
        "service_code": "VHS",
        "schema": ["SERVICES_BASE_SCHEMA"],
    },
    "lock_vehicle": {
        "function_name": "lock",
        "service_code": "RDL",
        "schema": ["SERVICES_BASE_SCHEMA", "SERVICES_PIN_SCHEMA"],
    },
    "unlock_vehicle": {
        "function_name": "unlock",
        "service_code": "RDU",
        "schema": ["SERVICES_BASE_SCHEMA", "SERVICES_PIN_SCHEMA"],
    },
    "reset_alarm": {
        "function_name": "reset_alarm",
        "service_code": "ALOFF",
        "schema": ["SERVICES_BASE_SCHEMA", "SERVICES_PIN_SCHEMA"],
    },
    "honk_blink": {
        "function_name": "honk_blink",
        "service_code": "HBLF",
        "schema": ["SERVICES_BASE_SCHEMA"],
    },
    "start_vehicle": {
        "function_name": "remote_engine_start",
        "service_code": "REON",
        "schema": [
            "SERVICES_BASE_SCHEMA",
            "SERVICES_PIN_SCHEMA",
            "SERVICES_TARGET_VALUE_SCHEMA",
        ],
    },
    "stop_vehicle": {
        "function_name": "remote_engine_stop",
        "service_code": "REOFF",
        "schema": ["SERVICES_BASE_SCHEMA", "SERVICES_PIN_SCHEMA"],
    },
    "start_charging": {
        "function_name": "charging_start",
        "service_code": "CP",
        "schema": ["SERVICES_BASE_SCHEMA"],
    },
    "stop_charging": {
        "function_name": "charging_stop",
        "service_code": "CP",
        "schema": ["SERVICES_BASE_SCHEMA"],
    },
    "start_preconditioning": {
        "function_name": "preconditioning_start",
        "service_code": "ECC",
        "schema": ["SERVICES_BASE_SCHEMA", "SERVICES_TARGET_TEMP_SCHEMA"],
    },
    "stop_preconditioning": {
        "function_name": "preconditioning_stop",
        "service_code": "ECC",
        "schema": ["SERVICES_BASE_SCHEMA"],
    },
    "set_max_charge_level": {
        "function_name": "set_max_soc",
        "service_code": "CP",
        "schema": ["SERVICES_BASE_SCHEMA", "SERVICES_CHARGE_LEVEL_SCHEMA"],
    },
    "set_one_off_max_charge_level": {
        "function_name": "set_one_off_max_soc",
        "service_code": "CP",
        "schema": ["SERVICES_BASE_SCHEMA", "SERVICES_CHARGE_LEVEL_SCHEMA"],
    },
}
