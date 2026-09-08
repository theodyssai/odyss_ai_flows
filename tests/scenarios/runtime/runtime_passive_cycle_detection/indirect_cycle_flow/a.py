from odyss_ai_flows import *


@node
async def a():
    return await nget("b")
