from odyss_ai_flows import *

import asyncio


@node
async def producer():

    await asyncio.sleep(
        0.02
    )

    return "producer_value"