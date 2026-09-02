def strip_non_blank(value):
    if value is None or not isinstance(value, str):
        return value

    normalized = value.strip()
    if not normalized:
        raise ValueError("No puede contener solamente espacios en blanco.")
    return normalized
