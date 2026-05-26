from odyss_ai_flows import *

import asyncio

from tests.scenarios.handlers_middleware_semantics.shared import (
    TRACE,
)


@node
async def ordered_node():

    await asyncio.sleep(
        0.05
    )

    TRACE.append(
        "ordered_node:node"
    )

    return {

        "ok":
            True
    }