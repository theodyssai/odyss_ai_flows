from odyss_ai_flows import *

import asyncio

from odyss_ai_flows.core.runtime.runner import (
    run_flow,
)

from odyss_ai_flows.core.utils.logger import (
    logger,
)


@node
async def root_node():

    logger.info(
        "TOP START"
    )

    await asyncio.sleep(
        0.01
    )

    nested = await run_flow(
        "nested_a"
    )

    logger.info(
        "TOP RESUMED"
    )

    await asyncio.sleep(
        0.01
    )

    return nested[
        "middle_node"
    ]