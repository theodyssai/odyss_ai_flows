from odyss_ai_flows import *

from tests.scenarios.handlers_middleware_semantics.shared import (
    TRACE,
)


@node
async def shorted_node():

    TRACE.append(
        "shorted_node:node"
    )

    raise RuntimeError(
        "node should not execute"
    )