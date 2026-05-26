from odyss_ai_flows import *

import asyncio


@node
async def producer():

    await asyncio.sleep(
        0.01
    )

    return "nested_value"