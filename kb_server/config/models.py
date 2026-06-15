import logging
from typing import Any, Optional

log = logging.getLogger("kb-mcp.config.models")

TYPE_MAP: dict[str, type] = {
    "string": str,
    "int": int,
    "float": float,
    "bool": bool,
    "json": str,
    "list": str,
}


def convert_value(value: str, type_name: str) -> Any:
    if value is None:
        return None
    if type_name == "bool":
        return value.lower() in ("1", "true", "yes", "on")
    if type_name == "int":
        try:
            return int(value)
        except (ValueError, TypeError):
            log.warning("Failed to convert '%s' to int, returning raw", value)
            return value
    if type_name == "float":
        try:
            return float(value)
        except (ValueError, TypeError):
            log.warning(
                "Failed to convert '%s' to float, returning raw", value
            )
            return value
    return value


def validate_type(value: str, type_name: str) -> Optional[str]:
    if type_name not in TYPE_MAP:
        return f"Unsupported type: {type_name}"
    if type_name == "bool":
        if value.lower() not in (
            "1",
            "0",
            "true",
            "false",
            "yes",
            "no",
            "on",
            "off",
        ):
            return f"Invalid bool value: {value}"
    elif type_name == "int":
        try:
            int(value)
        except (ValueError, TypeError):
            return f"Invalid int value: {value}"
    elif type_name == "float":
        try:
            float(value)
        except (ValueError, TypeError):
            return f"Invalid float value: {value}"
    return None
