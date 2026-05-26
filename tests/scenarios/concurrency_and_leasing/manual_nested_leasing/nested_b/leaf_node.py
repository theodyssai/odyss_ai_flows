from odyss_ai_flows import *

import asyncio

from odyss_ai_flows.core.utils.logger import (
    logger,
)


@node
async def leaf_node():

    logger.info(
        "NESTED B START"
    )

    await asyncio.sleep(
        0.01
    )

    logger.info(
        "NESTED B END"
    )

    return "done"