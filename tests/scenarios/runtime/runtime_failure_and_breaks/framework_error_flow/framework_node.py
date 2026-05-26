from odyss_ai_flows import *

from odyss_ai_flows.core.executor.exceptions import (
    FrameworkError,
)


@node
async def framework_node():

    await nget(
        "setup_node"
    )

    raise FrameworkError(
        RuntimeError(
            "intentional framework error"
        )
    )