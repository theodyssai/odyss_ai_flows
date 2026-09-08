from odyss_ai_flows import *


@node
async def b():
    return await nget("c")
