def enqueue(jobs, tenant, token, payload):
    if token in jobs:
        if jobs[token]["payload"] != payload:
            raise ValueError("conflict")
        return jobs[token]
    result = {"id": len(jobs) + 1, "payload": dict(payload)}
    jobs[token] = result
    return result
