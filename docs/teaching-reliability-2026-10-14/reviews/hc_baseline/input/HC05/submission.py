from decimal import Decimal, InvalidOperation
def cents(raw):
    try:
        value = Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError("invalid") from exc
    if not value.is_finite() or value < 0:
        raise ValueError("invalid")
    return int(value * 100)
