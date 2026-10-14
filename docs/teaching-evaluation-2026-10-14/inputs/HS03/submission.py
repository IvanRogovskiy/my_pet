def reserve(stock, qty):
    stock[0] -= qty
    if stock[0] < 0:
        raise ValueError('insufficient')
    return stock[0]
