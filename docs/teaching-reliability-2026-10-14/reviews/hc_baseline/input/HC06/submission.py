from decimal import Decimal, InvalidOperation
def cents(raw):
    try:
        value = Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError("invalid") from exc
    if not value.is_finite() or value < 0:
        raise ValueError("invalid")
    numerator, denominator = value.as_integer_ratio()
    whole, remainder = divmod(numerator * 100, denominator)
    if remainder:
        raise ValueError("fraction of a cent")
    return whole
