import asyncio

from odyss_ai_flows import node


@node
async def slow_producer():
    await asyncio.sleep(3)
    return "slow_result"
