from odyss_ai_flows import *

from odyss_ai_flows.core.runtime.runner import (
    run_flow,
)


@node
async def sibling_node():

    result = await run_flow(
        "nested_flow_a"
    )

    return {

        "nested_run_name":
            result["final_value"]["run_name"],
    }