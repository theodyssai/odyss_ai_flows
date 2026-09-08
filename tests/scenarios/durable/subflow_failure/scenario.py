from __future__ import annotations

import uuid

from odyss_ai_flows_durable import (
    PARALLEL_ORCHESTRATOR,
    DurableFlowStep,
    DurableRetryPolicy,
)

from tests.scenarios.durable._shared.client import assert_host_available, run_orchestration
from tests.scenarios.durable._shared.flows import flow_path

_FAIL = flow_path("fail_router")


async def _run(fail_times: int) -> dict:
    payload = {
        "steps": [
            DurableFlowStep(
                flow_name=_FAIL, name="router",
                inputs={"run_id": str(uuid.uuid4()), "fail_times": fail_times},
            ).to_dict(),
        ],
        "base_inputs": {},
        "retry_policy": DurableRetryPolicy(
            attempts=3, initial_delay_seconds=0.2, backoff=1.0
        ).to_dict(),
    }
    return await run_orchestration(PARALLEL_ORCHESTRATOR, payload)


async def run_scenario() -> None:
    await assert_host_available()

    # A permanently failing subflow fails the whole parent (the healthy sibling subflow's
    # success is not surfaced).
    permanent = await _run(fail_times=99)
    assert permanent["runtimeStatus"] == "Failed", permanent.get("output")

    # CHARACTERIZATION (§4.2): a subflow that fails exactly ONCE, under attempts=3, is STILL
    # fatal — the executor's DurableRetryPolicy never reaches subflow steps (schedule_step
    # builds the subflow's FlowOrchestrationInput without a retry_policy, and the subflow
    # dispatch happens outside the plan-level retry loop). Native retry is disabled on the
    # host, so nothing recovers it. Fixing the package (threading the policy through) would
    # flip this to "Completed" and fail this assertion — deliberately.
    recovers = await _run(fail_times=1)
    assert recovers["runtimeStatus"] == "Failed", (
        "expected fatal — DurableRetryPolicy does not reach subflow steps (§4.2); "
        f"got {recovers['runtimeStatus']}: {recovers.get('output')}"
    )
