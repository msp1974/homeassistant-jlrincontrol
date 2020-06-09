from homeassistant.const import TEMP_CELSIUS


def mask(str_value, from_start=0, from_end=0):
    str_mask = "x" * (len(str_value) - from_start - from_end)
    return f"{str_value[:from_start]}{str_mask}{str_value[-from_end:]}"


def convert_temp_value(temp_unit, service_code, target_value):
    """Convert from C/F to 31-57 needed for service call"""

    # Handle setting car units (prior to version 2.0)
    if target_value >= 31 and target_value <= 57:
        return target_value

    # Engine start/set rcc value
    if service_code == "REON":
        # Get temp units
        if temp_unit == TEMP_CELSIUS:
            # Convert from C
            return min(57, max(31, int(target_value * 2)))
        else:
            # Convert from F
            return min(57, max(31, target_value - 27))

    # Climate preconditioning
    if service_code == "ECC":
        if temp_unit == TEMP_CELSIUS:
            return min(285, max(155, int(target_value * 10)))
        else:
            # Convert from F
            return min(285, max(155, int(((target_value - 27) / 2) * 10)))
