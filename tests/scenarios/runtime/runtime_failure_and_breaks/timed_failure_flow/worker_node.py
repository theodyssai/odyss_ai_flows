from odyss_ai_flows import *

import asyncio


@node
async def worker_node():

    await nget(
        "setup_node"
    )

    await asyncio.sleep(
        0.5
    )

    return "worker_complete"