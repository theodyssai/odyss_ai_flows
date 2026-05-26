from odyss_ai_flows import *

from odyss_ai_flows.core.runtime.runner import (
    run_flow,
)


@node
async def propagation_node():

    result = await run_flow(
        "nested_flow_a"
    )

    return {

        "nested_value":
            result["final_value"]["value"],
    }