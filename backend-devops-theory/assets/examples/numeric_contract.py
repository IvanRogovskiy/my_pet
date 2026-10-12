"""Exact positive integer JSON contract, with an explicit example range (not global policy)."""
import json
from decimal import Decimal


def reject_constant(value):
    raise ValueError("non-finite JSON number")


def quantity_from_json(raw, maximum=1000):
    """Parse the original token, reject bool/string/fraction, bound before converting to int."""
    value = json.loads(raw, parse_int=Decimal, parse_float=Decimal, parse_constant=reject_constant)
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ValueError("quantity must be a finite JSON number")
    if not 1 <= value <= maximum or value != value.to_integral_value():
        raise ValueError("quantity must be an integer within the declared range")
    return int(value)


if __name__ == "__main__":
    for raw in ["1", "1.0", "1e0", "true", '"1"', "1.5", "-1", "1.0000000000000001", "1e-10000", "1e10000"]:
        try:
            result = quantity_from_json(raw)
        except ValueError:
            result = "rejected"
        print(json.dumps({"raw": raw, "result": result}))
