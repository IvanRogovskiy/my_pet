def submit(state, buyer, key, payload):
    if key in state:
        return state[key]
    result = {"id": len(state) + 1, "payload": dict(payload)}
    state[key] = result
    return result
