from __future__ import annotations

from odyss_ai_flows_durable import PARALLEL_ORCHESTRATOR, DurableFlowStep

from tests.scenarios.durable._shared.client import assert_host_available, run_orchestration
from tests.scenarios.durable._shared.flows import flow_path

_NESTED = flow_path("nested_router")


async def run_scenario() -> None:
    await assert_host_available()

    # nested_router dispatches two branches, each running fanout_router (whose node returns
    # another DurableSubflowOutput) -> 2 levels of recursive subflow dispatch.
    payload = {
        "steps": [DurableFlowStep(flow_name=_NESTED, name="router").to_dict()],
        "base_inputs": {},
    }

    status = await run_orchestration(PARALLEL_ORCHESTRATOR, payload)
    assert status["runtimeStatus"] == "Completed", status.get("output")

    top = status["output"]["flow_results"]["router"]["subflow_results"]["__default__"]

    # Each branch's own subflow_results are spliced back in under the branch's entry.
    branch_0 = top["branch_0"]
    assert branch_0["router"]["data"] == {"count": 2}, branch_0["router"]
    inner_0 = branch_0["subflow_results"]["__default__"]
    assert inner_0["item_0"] == {"echo": "x1"}, inner_0
    assert inner_0["item_1"] == {"echo": "x2"}, inner_0

    branch_1 = top["branch_1"]
    assert branch_1["router"]["data"] == {"count": 1}, branch_1["router"]
    inner_1 = branch_1["subflow_results"]["__default__"]
    assert inner_1["item_0"] == {"echo": "y1"}, inner_1
