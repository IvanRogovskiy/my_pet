def total(items):
    result = 0
    for item in items:
        result = result + item["price"] * item["qty"]
    return result
