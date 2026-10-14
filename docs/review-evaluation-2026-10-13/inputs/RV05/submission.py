def validate(value):
    if type(value) is not int or value < 0:
        raise ValueError("invalid money")
    return value
