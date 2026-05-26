from odyss_ai_flows import *

import asyncio

from tests.scenarios.handlers_middleware_semantics.shared import (
    TRACE,
)

from tests.scenarios.handlers_middleware_semantics.isolated_flow.node_a import (
    node_a,
)


@node
async def node_b():

    await nget(
        node_a
    )

    await asyncio.sleep(
        0.05
    )

    TRACE.append(
        "node_b:node"
    )

    return "b"