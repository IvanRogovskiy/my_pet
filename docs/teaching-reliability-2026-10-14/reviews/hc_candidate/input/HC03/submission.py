def debit(wallet, amount):
    before = wallet
    wallet["balance"] -= amount
    if wallet["balance"] < 0:
        wallet.update(before)
        raise ValueError("insufficient")
    return wallet["balance"]
