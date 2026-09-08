from odyss_ai_flows import *


@node
async def c():

    return await nget("a")
