from odyss_ai_flows import *


@node
async def b():
    result = await nget("a")
    return result + 1
