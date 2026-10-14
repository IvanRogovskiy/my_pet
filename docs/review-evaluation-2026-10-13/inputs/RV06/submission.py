def validate(value):
    if isinstance(value, bool):
        raise ValueError("boolean")
    if not isinstance(value, int) or value < 0:
        raise ValueError("invalid money")
    return value
