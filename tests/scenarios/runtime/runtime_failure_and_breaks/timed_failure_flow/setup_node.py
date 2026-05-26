from odyss_ai_flows import *

import asyncio


@node
async def setup_node():

    await asyncio.sleep(
        0.1
    )

    return "setup_complete"