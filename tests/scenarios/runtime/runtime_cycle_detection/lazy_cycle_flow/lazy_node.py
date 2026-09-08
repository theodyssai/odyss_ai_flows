from odyss_ai_flows import *


@node
async def lazy_node():

    return await nget("eager_node")
