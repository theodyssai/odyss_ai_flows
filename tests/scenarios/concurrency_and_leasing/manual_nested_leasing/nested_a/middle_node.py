from odyss_ai_flows import *

import asyncio

from odyss_ai_flows.core.runtime.runner import (
    run_flow,
)

from odyss_ai_flows.core.utils.logger import (
    logger,
)


@node
async def middle_node():

    logger.info(
        "NESTED A START"
    )

    await asyncio.sleep(
        0.01
    )

    nested = await run_flow(
        "nested_b"
    )

    logger.info(
        "NESTED A RESUMED"
    )

    await asyncio.sleep(
        0.01
    )

    return nested[
        "leaf_node"
    ]