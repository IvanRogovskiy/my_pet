def quantity(value):
    if type(value) is not int or value <= 0:
        raise ValueError("invalid quantity")
    return value
