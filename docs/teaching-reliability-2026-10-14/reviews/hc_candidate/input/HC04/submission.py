def debit(wallet, amount):
    remaining = wallet["balance"] - amount
    if remaining < 0:
        raise ValueError("insufficient")
    wallet["balance"] = remaining
    return remaining
