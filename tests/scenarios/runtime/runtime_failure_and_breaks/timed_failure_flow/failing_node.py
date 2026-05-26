from odyss_ai_flows import *

import asyncio


@node
async def failing_node():

    await nget(
        "setup_node"
    )

    await asyncio.sleep(
        0.2
    )

    raise RuntimeError(
        "timed overlapping failure"
    )