from datetime import datetime


def validate_required(value, field_name: str) -> tuple[bool, str]:
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return False, f"{field_name} is required."
    return True, ""


def validate_non_negative_int(value, field_name: str) -> tuple[bool, str]:
    """Validates that value is a non-negative integer (0 or greater)."""
    if value is None or value == "":
        return True, ""
    try:
        v = int(value)
        if v < 0:
            return False, f"{field_name} must be 0 or greater."
        return True, ""
    except (ValueError, TypeError):
        return False, f"{field_name} must be a valid integer."


# Backward-compatible alias
validate_positive_int = validate_non_negative_int


def validate_percentage(value, field_name: str) -> tuple[bool, str]:
    if value is None or value == "":
        return True, ""
    try:
        v = float(value)
        if v < 0 or v > 100:
            return False, f"{field_name} must be between 0 and 100."
        return True, ""
    except (ValueError, TypeError):
        return False, f"{field_name} must be a valid number."


def validate_year(value, field_name: str = "Year") -> tuple[bool, str]:
    if value is None or value == "":
        return False, f"{field_name} is required."
    try:
        v = int(value)
        current_year = datetime.now().year
        if v < 1900 or v > current_year + 1:
            return False, f"{field_name} must be between 1900 and {current_year + 1}."
        return True, ""
    except (ValueError, TypeError):
        return False, f"{field_name} must be a valid year."


def validate_float(value, field_name: str) -> tuple[bool, str]:
    if value is None or value == "":
        return True, ""
    try:
        float(value)
        return True, ""
    except (ValueError, TypeError):
        return False, f"{field_name} must be a valid number."


def parse_int(value, default=None):
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def parse_float(value, default=None):
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default
