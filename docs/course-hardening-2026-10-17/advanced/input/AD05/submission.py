async def reserve(state, trace):
    before = state[0]
    trace.append(("read", before))
    state[0] = before - 1
    trace.append(("write", state[0]))
    return state[0]
