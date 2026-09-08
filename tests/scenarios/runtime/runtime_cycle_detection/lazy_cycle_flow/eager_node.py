from odyss_ai_flows import *


@node
async def eager_node():

    return await nget("lazy_node")
