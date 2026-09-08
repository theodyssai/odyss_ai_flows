from typing import Union

MetadataValue = Union[str, int, float, bool, None]
META_TYPES = ("str", "int", "float", "bool", "null")


def validate_metadata_value(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return
    raise TypeError(
        f"Unsupported metadata value type: {type(value).__name__}. "
        f"Allowed: str, int, float, bool, None."
    )


def serialize_metadata_value(value):
    validate_metadata_value(value)
    if value is None:
        return None, "null"
    if isinstance(value, bool):
        return ("1" if value else "0"), "bool"
    if isinstance(value, int):
        return str(value), "int"
    if isinstance(value, float):
        return repr(value), "float"
    return value, "str"


def deserialize_metadata_value(raw, type_tag):
    if type_tag == "null":
        return None
    if type_tag == "bool":
        return raw == "1"
    if type_tag == "int":
        return int(raw)
    if type_tag == "float":
        return float(raw)
    if type_tag == "str":
        return raw
    raise ValueError(f"Unknown metadata type tag: {type_tag!r}")
