from __future__ import annotations

import uuid

from odyss_ai_flows_durable import (
    PARALLEL_ORCHESTRATOR,
    DurableFlowStep,
    DurableRetryPolicy,
)

from tests.scenarios.durable._shared.client import assert_host_available, run_orchestration
from tests.scenarios.durable._shared.flows import flow_path

_FLAKY = flow_path("flaky")


def _payload(fail_times: int, attempts: int) -> dict:
    return {
        "steps": [
            DurableFlowStep(
                flow_name=_FLAKY,
                name="healthy_a",
                inputs={"run_id": str(uuid.uuid4()), "fail_times": 0},
            ).to_dict(),
            DurableFlowStep(
                flow_name=_FLAKY,
                name="healthy_b",
                inputs={"run_id": str(uuid.uuid4()), "fail_times": 0},
            ).to_dict(),
            DurableFlowStep(
                flow_name=_FLAKY,
                name="flaky",
                inputs={"run_id": str(uuid.uuid4()), "fail_times": fail_times},
            ).to_dict(),
        ],
        "base_inputs": {},
        "retry_policy": DurableRetryPolicy(
            attempts=attempts, initial_delay_seconds=0.2, backoff=1.0
        ).to_dict(),
    }


async def run_scenario() -> None:
    await assert_host_available()

    # --- only the failed step is retried; healthy siblings are not re-run -------
    # (native retry is disabled on the host, so the DurableRetryPolicy is the sole layer.)
    recovers = await run_orchestration(PARALLEL_ORCHESTRATOR, _payload(fail_times=1, attempts=3))
    assert recovers["runtimeStatus"] == "Completed", recovers.get("output")
    fr = recovers["output"]["flow_results"]
    assert fr["flaky"]["flaky"]["attempt"] == 2, fr["flaky"]
    assert fr["healthy_a"]["flaky"]["attempt"] == 1, fr["healthy_a"]
    assert fr["healthy_b"]["flaky"]["attempt"] == 1, fr["healthy_b"]

    # --- all-or-nothing: exhausting retries fails the whole orchestration. --------
    exhausted = await run_orchestration(PARALLEL_ORCHESTRATOR, _payload(fail_times=99, attempts=2))
    assert exhausted["runtimeStatus"] == "Failed", exhausted.get("output")
