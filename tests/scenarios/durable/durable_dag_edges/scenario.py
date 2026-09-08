from __future__ import annotations

import uuid

from odyss_ai_flows_durable import FLOW_ORCHESTRATOR, FlowOrchestrationInput

from tests.scenarios.durable._shared.client import (
    assert_host_available,
    get_instance_status,
    start_orchestration,
    terminate_instance,
    terminate_orchestration,
    wait_for_completion,
    wait_for_instance_completion,
    wait_for_terminal,
)
from tests.scenarios.durable._shared.flows import flow_path

_CYCLE = flow_path("dag_cycle")
_FLAKY = flow_path("flaky")
_INDIRECT = flow_path("dag_indirect")
_LINEAR = flow_path("dag_linear")


async def _run(flow: str, inputs: dict | None = None) -> dict:
    started = await start_orchestration(
        FLOW_ORCHESTRATOR,
        FlowOrchestrationInput(flow_name=flow, inputs=inputs or {}).to_dict(),
    )
    return await wait_for_completion(started["statusQueryGetUri"])


async def run_scenario() -> None:
    await assert_host_available()

    # A caller-supplied parent ID is used verbatim and deterministically prefixes
    # every node sub-orchestration ID.
    parent_id = f"dag-parent-{uuid.uuid4()}"
    started = await start_orchestration(
        FLOW_ORCHESTRATOR,
        FlowOrchestrationInput(flow_name=_LINEAR, inputs={}).to_dict(),
        instance_id=parent_id,
    )
    completed = await wait_for_completion(started["statusQueryGetUri"])
    assert completed["runtimeStatus"] == "Completed", completed.get("output")
    for node in ("step_a", "step_b"):
        child = await get_instance_status(f"{parent_id}_{node}")
        assert child["runtimeStatus"] == "Completed", child

    # With no policy and the test host's native retry disabled, a failing node
    # makes the single-flow orchestration fail immediately.
    failed = await _run(
        _FLAKY,
        {"run_id": str(uuid.uuid4()), "fail_times": 99},
    )
    assert failed["runtimeStatus"] == "Failed", failed.get("output")
    assert "forced failure" in str(failed.get("output")), failed.get("output")

    # A non-literal nget works in core but has no durable DAG edge. The runtime
    # fails loudly because producer was not prelaunched; it does not silently race.
    indirect = await _run(_INDIRECT)
    assert indirect["runtimeStatus"] == "Failed", indirect.get("output")
    assert "not prelaunched" in str(indirect.get("output")), indirect.get("output")

    # CHARACTERIZATION: PR 69's cycle detection (assert_dag_acyclic -> OrchestrationError) runs
    # only on DurableFunctionsExecutor.start(), NOT the FLOW_ORCHESTRATOR path used here, so a
    # cycle driven via the management API still parks forever with no event timeout. (The
    # detection itself is unit-tested in unit_build_dag.) Bound the observation and always
    # terminate the instance so the suite cannot leave a wedged task-hub orchestration behind.
    cycle_id = f"dag-cycle-{uuid.uuid4()}"
    cycle = await start_orchestration(
        FLOW_ORCHESTRATOR,
        FlowOrchestrationInput(flow_name=_CYCLE, inputs={}).to_dict(),
        instance_id=cycle_id,
    )
    try:
        terminal = await wait_for_terminal(
            cycle["statusQueryGetUri"],
            timeout=5.0,
        )
        assert terminal is None, (
            "cyclic flow unexpectedly reached a terminal state: "
            f"{terminal and terminal.get('runtimeStatus')}"
        )
        current = await get_instance_status(cycle_id)
        assert current["runtimeStatus"] in {"Pending", "Running"}, current
    finally:
        # Terminating a parent orchestration does not recursively terminate its
        # node sub-orchestrations, so clean up both parked children explicitly.
        for node in ("node_a", "node_b"):
            await terminate_instance(
                f"{cycle_id}_{node}",
                reason="durable test cycle child cleanup",
            )
        await terminate_orchestration(
            cycle["terminatePostUri"],
            reason="durable test cycle cleanup",
        )

    terminated = await wait_for_completion(
        cycle["statusQueryGetUri"],
        timeout=15.0,
    )
    assert terminated["runtimeStatus"] == "Terminated", terminated
    for node in ("node_a", "node_b"):
        child = await wait_for_instance_completion(
            f"{cycle_id}_{node}",
            timeout=15.0,
        )
        assert child["runtimeStatus"] == "Terminated", child
