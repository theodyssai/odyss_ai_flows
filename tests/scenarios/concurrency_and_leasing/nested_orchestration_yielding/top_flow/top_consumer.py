from odyss_ai_flows import *

import asyncio

from odyss_ai_flows.core.runtime.runner import (
    run_flow,
)

from tests.scenarios.concurrency_and_leasing.nested_orchestration_yielding.top_flow.top_producer import (
    top_producer,
)


@node
async def top_consumer():

    await asyncio.sleep(
        0.01
    )

    value = await nget(
        top_producer
    )

    await asyncio.sleep(
        0.01
    )

    nested = await run_flow(
        "nested_flow"
    )

    await asyncio.sleep(
        0.01
    )

    return {

        "top":
            value,

        "nested":
            nested[
                "consumer"
            ],
    }