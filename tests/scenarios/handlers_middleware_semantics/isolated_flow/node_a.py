from odyss_ai_flows import *

import asyncio

from tests.scenarios.handlers_middleware_semantics.shared import (
    TRACE,
)


@node
async def node_a():

    await asyncio.sleep(
        0.05
    )

    TRACE.append(
        "node_a:node"
    )

    return "a"