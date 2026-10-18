def allocate(stock, requests):
    requests.sort()
    if any(stock[sku] < qty for sku, qty in requests):
        raise ValueError("insufficient")
    for sku, qty in requests:
        stock[sku] -= qty
    return stock
