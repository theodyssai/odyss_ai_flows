from odyss_ai_flows import *

import asyncio

from tests.scenarios.concurrency_and_leasing.custom_strategy_injection.flow.producer import (
    producer,
)


@node
async def consumer():

    await asyncio.sleep(
        0.02
    )

    value = await nget(
        producer
    )

    return value