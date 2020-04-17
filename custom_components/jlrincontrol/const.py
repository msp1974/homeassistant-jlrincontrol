import logging

_LOGGER = logging.getLogger(__name__)

DOMAIN = "jlrincontrol"
DATA_JLR_CONFIG = "jlr_config"
VERSION = "0.1.0"
SCAN_INTERVAL = 60


# Conversions
KMS_TO_MILES = 0.62137

SIGNAL_STATE_UPDATED = f"{DOMAIN}.updated"


SENSOR_TYPES = {
    "lids": ["Doors", "opening", "mdi:car-door-lock"],
    "windows": ["Windows", "opening", "mdi:car-door"],
    "door_lock_state": ["Door lock state", "lock", "mdi:car-key"],
    "lights_parking": ["Parking lights", "light", "mdi:car-parking-lights"],
    "condition_based_services": ["Condition based services", "problem", "mdi:wrench"],
    "check_control_messages": ["Control messages", "problem", "mdi:car-tire-alert"],
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
}

SERVICE_STATUS_OK = ["CLEAR", "FUNCTIONING", "NORMAL", "NORMAL_UNBLOCKED"]
