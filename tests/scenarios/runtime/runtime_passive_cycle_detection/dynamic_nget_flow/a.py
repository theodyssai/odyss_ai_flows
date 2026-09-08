from odyss_ai_flows import *


@node
async def a():
    target = "b"
    return await nget(target)
