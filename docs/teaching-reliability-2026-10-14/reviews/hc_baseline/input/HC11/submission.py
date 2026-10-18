def label(value):
    if not isinstance(value, str) or not value:
        raise ValueError("invalid")
    return value
