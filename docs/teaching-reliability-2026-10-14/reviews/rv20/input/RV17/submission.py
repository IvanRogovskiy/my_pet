import json
import math

def quantity(raw):
    value = json.loads(raw)
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError("invalid quantity")
    if not 1 <= value <= 1000 or int(value) != value:
        raise ValueError("invalid quantity")
    return int(value)
