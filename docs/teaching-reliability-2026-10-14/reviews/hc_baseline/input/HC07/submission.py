def remember(cache, tenant, token, body):
    key = (tenant, token)
    if key in cache:
        old = cache[key]
        if set(old["body"]) != set(body):
            raise ValueError("conflict")
        return old
    result = {"id": len(cache) + 1, "body": dict(body)}
    cache[key] = result
    return result
