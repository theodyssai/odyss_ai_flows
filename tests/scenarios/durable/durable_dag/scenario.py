from __future__ import annotations

import time

from odyss_ai_flows_durable import FLOW_ORCHESTRATOR, FlowOrchestrationInput

from tests.scenarios.durable._shared.client import assert_host_available, run_orchestration
from tests.scenarios.durable._shared.flows import flow_path

_LINEAR = flow_path("dag_linear")
_FAN = flow_path("dag_fan")
_SLOW = flow_path("dag_slow")


async def _run(flow: str, *, timeout: float = 60.0) -> dict:
    status = await run_orchestration(
        FLOW_ORCHESTRATOR, FlowOrchestrationInput(flow_name=flow, inputs={}).to_dict(), timeout=timeout
    )
    assert status["runtimeStatus"] == "Completed", status.get("output")
    return status["output"]


async def run_scenario() -> None:
    await assert_host_available()

    # Linear chain: a dependency-event signal carries step_a's result to step_b.
    linear = await _run(_LINEAR)
    assert linear["step_a"] == "result_a", linear
    assert linear["step_b"] == "step_b got result_a", linear

    # Fan-out / fan-in: one source, three branches, an aggregator that task_all's 3 events.
    fan = await _run(_FAN)
    assert (fan["source"], fan["branch_a"], fan["branch_b"], fan["branch_c"], fan["aggregator"]) \
        == (10, 20, 30, 40, 90), fan

    # Long-running dependency: a real multi-second wait survives via durable timers/events
    # (not an in-memory future) — assert the wall-clock elapsed actually covers the sleep.
    start = time.monotonic()
    slow = await _run(_SLOW, timeout=30.0)
    elapsed = time.monotonic() - start
    assert slow["slow_producer"] == "slow_result", slow
    assert slow["consumer_a"] == "a:slow_result" and slow["consumer_b"] == "b:slow_result", slow
    assert elapsed >= 3.0, f"expected >= 3s (slow_producer sleep), got {elapsed:.1f}s"
