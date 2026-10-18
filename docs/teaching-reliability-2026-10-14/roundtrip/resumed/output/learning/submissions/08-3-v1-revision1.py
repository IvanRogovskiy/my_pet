def submit(state, buyer, key, payload):
    scoped = (buyer, key)
    if scoped in state:
        return state[scoped]
    result = {'id': len(state)+1, 'payload': dict(payload)}
    state[scoped] = result
    return result
