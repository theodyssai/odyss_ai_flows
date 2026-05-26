from odyss_ai_flows import *

import asyncio

from tests.scenarios.concurrency_and_leasing.nested_orchestration_yielding.nested_flow.producer import (
    producer,
)


@node
async def consumer():

    await asyncio.sleep(
        0.01
    )

    value = await nget(
        producer
    )

    await asyncio.sleep(
        0.01
    )

    return value