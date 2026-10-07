def validate(value):
    if isinstance(value, int) and value >= 0:
        return value
    raise ValueError("invalid money")
