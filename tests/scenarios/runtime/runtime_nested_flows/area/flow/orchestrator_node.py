from odyss_ai_flows import *

from odyss_ai_flows.core.runtime.runner import (
    run_flow,
)


@node
async def orchestrator_node():

    first = await run_flow(
        "nested_flow_a"
    )

    second = await run_flow(
        "nested_flow_a"
    )

    third = await run_flow(
        "nested_flow_b",
        run_name="manual_nested_run",
    )

    return {

        "nested_run_names": [

            first["final_value"]["run_name"],
            second["final_value"]["run_name"],
            third["final_value"]["run_name"],
        ],

        "top_names": [

            first["final_value"]["top_name"],
            second["final_value"]["top_name"],
            third["final_value"]["top_name"],
        ],
    }