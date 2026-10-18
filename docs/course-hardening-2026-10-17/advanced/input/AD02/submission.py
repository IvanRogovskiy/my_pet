from copy import deepcopy
def enqueue(jobs, tenant, token, payload):
    scope = (tenant, token)
    frozen = tuple(sorted((key, tuple(values)) for key, values in payload.items()))
    if scope in jobs:
        old = jobs[scope]
        if old["fingerprint"] != frozen:
            raise ValueError("conflict")
        return old["result"]
    result = {"id": len(jobs) + 1, "payload": deepcopy(payload)}
    jobs[scope] = {"fingerprint": frozen, "result": result}
    return result
