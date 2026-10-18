def can_read(actor, order, request):
    return actor["role"] == "admin" or actor["id"] == order["owner_id"]
