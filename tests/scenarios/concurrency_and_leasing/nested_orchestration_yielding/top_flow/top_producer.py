from odyss_ai_flows import *

import asyncio


@node
async def top_producer():

    await asyncio.sleep(
        0.01
    )

    return "top_value"