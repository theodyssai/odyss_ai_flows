from odyss_ai_flows import *


@node
async def c():

    a = await nget("a")
    b = await nget("b")
    return a + b
