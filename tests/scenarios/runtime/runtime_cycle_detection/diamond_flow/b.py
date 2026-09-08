from odyss_ai_flows import *


@node
async def b():

    d = await nget("d")
    return d + 2
