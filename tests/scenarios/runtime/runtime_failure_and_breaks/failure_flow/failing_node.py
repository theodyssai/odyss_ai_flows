from odyss_ai_flows import *


@node
async def failing_node():

    await nget(
        "setup_node"
    )

    raise ValueError(
        "intentional node failure"
    )