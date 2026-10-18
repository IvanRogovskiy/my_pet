def remember(cache, tenant, token, body):
    key = (tenant, token)
    if key in cache:
        if cache[key]["body"] != body:
            raise ValueError("conflict")
        return cache[key]
    result = {"id": len(cache) + 1, "body": dict(body)}
    cache[key] = result
    return result
