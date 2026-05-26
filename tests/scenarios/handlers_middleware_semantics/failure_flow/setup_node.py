from odyss_ai_flows import *

import asyncio

from tests.scenarios.handlers_middleware_semantics.shared import (
    TRACE,
)


@node
async def setup_node():

    await asyncio.sleep(
        0.05
    )

    TRACE.append(
        "setup_node:node"
    )

    return "setup"