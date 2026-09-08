from __future__ import annotations

from odyss_ai_flows_durable import PARALLEL_ORCHESTRATOR, DurableFlowStep

from tests.scenarios.durable._shared.client import assert_host_available, run_orchestration
from tests.scenarios.durable._shared.flows import flow_path

_STAGED = flow_path("staged_router")
_STAGE_PROBE = flow_path("stage_probe_router")


async def _subflow_results(flow: str, inputs: dict) -> dict:
    status = await run_orchestration(PARALLEL_ORCHESTRATOR, {
        "steps": [DurableFlowStep(flow_name=flow, name="router", inputs=inputs).to_dict()],
        "base_inputs": {},
    })
    assert status["runtimeStatus"] == "Completed", status.get("output")
    return status["output"]["flow_results"]["router"]["subflow_results"]


async def _consume_echo_in(inputs: dict) -> str:
    sub = await _subflow_results(_STAGE_PROBE, inputs)
    # subflow_results[group][step_key] is the probe FLOW's result, keyed by its node name.
    return sub["consume"]["check"]["probe"]["echo_in"]


async def run_scenario() -> None:
    await assert_host_available()

    # --- host integration: staged-group result shape -----------------------------
    # Exact max_concurrent batching is asserted deterministically in
    # unit_subflow_scheduling; Azurite is not used as a wall-clock oracle (§4.9).
    sub = await _subflow_results(_STAGED, {"items": ["p", "q", "r"]})
    assert list(sub) == ["fetch", "notify"], sub
    assert sub["fetch"]["fetch_0"] == {"echo": "p"}, sub["fetch"]
    assert sub["fetch"]["fetch_1"] == {"echo": "q"}, sub["fetch"]
    assert sub["fetch"]["fetch_2"] == {"echo": "r"}, sub["fetch"]
    assert sub["notify"]["notify"] == {"echo": "done"}, sub["notify"]

    # --- skip_group_output + default_group_config inherit/override -------------
    # "produce" forwards echo's output (output_keys=["echo"]); "consume" probes for it.
    assert await _consume_echo_in({"skip": True}) == "ABSENT"                    # not propagated
    assert await _consume_echo_in({"skip": False}) == "secret"                   # propagated
    assert await _consume_echo_in({"default_skip": True}) == "ABSENT"            # inherits skip=True
    assert await _consume_echo_in({"default_skip": True, "skip": False}) == "secret"  # override wins
