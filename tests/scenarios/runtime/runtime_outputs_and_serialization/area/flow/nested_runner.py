from odyss_ai_flows import *

from odyss_ai_flows.core.runtime.runner import (
    run_flow,
)


@node
async def nested_runner():

    nested = await run_flow(
        "nested_flow"
    )

    return nested