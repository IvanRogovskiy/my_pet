import asyncio
from submission import reserve
def test_overlap():
    async def run():
        state, trace = [2], []
        await asyncio.gather(reserve(state, trace), reserve(state, trace))
        assert len(trace) == 4
    asyncio.run(run())
