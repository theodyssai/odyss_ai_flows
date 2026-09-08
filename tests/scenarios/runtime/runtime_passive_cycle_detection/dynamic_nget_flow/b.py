from odyss_ai_flows import *


@node
async def b():
    target = "a"
    return await nget(target)
