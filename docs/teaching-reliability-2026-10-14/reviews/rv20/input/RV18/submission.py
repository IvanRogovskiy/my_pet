import json
from decimal import Decimal, InvalidOperation

def quantity(raw):
    try:
        value = json.loads(raw, parse_float=Decimal, parse_int=Decimal,
                           parse_constant=Decimal)
    except InvalidOperation as exc:
        raise ValueError("invalid quantity") from exc
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ValueError("invalid quantity")
    if not 1 <= value <= 1000 or value != value.to_integral_value():
        raise ValueError("invalid quantity")
    return int(value)
