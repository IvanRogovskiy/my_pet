from collections import Counter
def allocate(stock, requests):
    totals = Counter()
    for sku, qty in requests:
        totals[sku] += qty
    after = {sku: stock[sku] - qty for sku, qty in totals.items()}
    if any(value < 0 for value in after.values()):
        raise ValueError("insufficient")
    stock.update(after)
    return stock
