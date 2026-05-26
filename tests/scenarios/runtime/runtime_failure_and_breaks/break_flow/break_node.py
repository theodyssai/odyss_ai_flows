from odyss_ai_flows import *

from odyss_ai_flows.core.executor.exceptions import (
    FlowBreak,
)


@node
async def break_node():

    await nget(
        "setup_node"
    )

    raise FlowBreak(
        "intentional break"
    )