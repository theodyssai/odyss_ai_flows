from odyss_ai_flows import *


@node
async def a():

    d = await nget("d")
    return d + 1
