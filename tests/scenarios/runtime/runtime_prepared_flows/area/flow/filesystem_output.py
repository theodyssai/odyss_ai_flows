from odyss_ai_flows import *


async def filesystem_output():

    value = await nget(
        "filesystem_node"
    )

    return value