from __future__ import annotations

import uuid

from odyss_ai_flows_durable import (
    SEQUENCE_ORCHESTRATOR,
    DispatchMode,
    DurableFlowStep,
    DurableRetryPolicy,
)

from tests.scenarios.durable._shared.client import (
    assert_host_available,
    run_orchestration,
)
from tests.scenarios.durable._shared.flows import flow_path

_FLAKY = flow_path("flaky")
_SIDE_EFFECT = flow_path("side_effect_flow")
_POLICY = DurableRetryPolicy(
    attempts=3,
    initial_delay_seconds=0.2,
    backoff=1.0,
)


async def _run(steps: list[DurableFlowStep]) -> dict:
    return await run_orchestration(SEQUENCE_ORCHESTRATOR, {
        "steps": [step.to_dict() for step in steps],
        "base_inputs": {},
        "retry_policy": _POLICY.to_dict(),
    })


async def run_scenario() -> None:
    await assert_host_available()

    # Sequence retry has its own implementation: an earlier successful step stays
    # at attempt 1 while only the failing current step is rescheduled.
    recovered = await _run([
        DurableFlowStep(
            flow_name=_FLAKY,
            name="healthy",
            inputs={"run_id": str(uuid.uuid4()), "fail_times": 0},
        ),
        DurableFlowStep(
            flow_name=_FLAKY,
            name="retrying",
            inputs={"run_id": str(uuid.uuid4()), "fail_times": 1},
        ),
    ])
    assert recovered["runtimeStatus"] == "Completed", recovered.get("output")
    results = recovered["output"]["flow_results"]
    assert results["healthy"]["flaky"]["attempt"] == 1, results["healthy"]
    assert results["retrying"]["flaky"]["attempt"] == 2, results["retrying"]

    exhausted = await _run([
        DurableFlowStep(
            flow_name=_FLAKY,
            name="never",
            inputs={"run_id": str(uuid.uuid4()), "fail_times": 99},
        ),
    ])
    assert exhausted["runtimeStatus"] == "Failed", exhausted.get("output")

    # CHARACTERIZATION: plan-level retry creates a fresh flow execution in BOTH
    # dispatch modes. A completed side-effect node therefore executes twice when a
    # later node fails once, even for a DURABLE step.
    for mode in (DispatchMode.DIRECT, DispatchMode.DURABLE):
        retried = await _run([
            DurableFlowStep(
                flow_name=_SIDE_EFFECT,
                name="step",
                mode=mode,
                inputs={
                    "run_id": str(uuid.uuid4()),
                    "fail_times": 1,
                },
            ),
        ])
        assert retried["runtimeStatus"] == "Completed", (
            mode,
            retried.get("output"),
        )
        step_result = retried["output"]["flow_results"]["step"]
        assert step_result["finish"] == {
            "attempt": 2,
            "effect_count": 2,
        }, (mode, step_result)
