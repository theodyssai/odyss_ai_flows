from __future__ import annotations

from pathlib import Path

from odyss_ai_flows import run_flow
from odyss_ai_flows_durable import run_durable_flow


async def run_scenario() -> None:
    flow_dir = Path(__file__).parent / "flow"

    core_result = await run_flow(flow_dir)
    durable_result = await run_durable_flow(flow_dir)

    assert core_result["producer"] == "hello from producer"
    assert core_result["consumer"] == "hello from producer via consumer"

    # With no executor, the plugin is a transparent pass-through to core run_flow.
    assert durable_result.status == core_result.status
    assert durable_result.outputs == core_result.outputs
    assert durable_result.all_node_results == core_result.all_node_results
