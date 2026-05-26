from odyss_ai_flows import *

from tests.scenarios.handlers_middleware_semantics.failure_flow.setup_node import (
    setup_node,
)


@node
async def failing_node():

    await nget(
        setup_node
    )

    return "unreachable"