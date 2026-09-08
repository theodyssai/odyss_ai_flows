from __future__ import annotations

from pathlib import Path
from typing import Any

from odyss_ai_flows_durable import (
    FLOW_ORCHESTRATOR,
    PARALLEL_ORCHESTRATOR,
    SEQUENCE_ORCHESTRATOR,
    DurableFlowExecutor,
    DurableFlowPlan,
    DurableFlowStep,
    DurableFunctionsExecutor,
    DurableParallelExecutor,
    DurableRetryPolicy,
    DurableSequenceExecutor,
    run_durable_flow,
)
from odyss_ai_flows_durable._runtime._single.executor import _DagOrchestrator

_FLOW = Path(__file__).resolve().parents[1] / "_flows" / "dag_linear"


class _RecordingClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def start_new(self, **kwargs) -> str:
        self.calls.append(kwargs)
        return kwargs.get("instance_id") or "generated-instance"


class _DagContext:
    def __init__(self) -> None:
        self.sub_calls: list[dict[str, Any]] = []
        self.task_all_calls: list[list[Any]] = []

    def call_sub_orchestrator_with_retry(
        self, name, retry_options, *, input_, instance_id
    ):
        call = {
            "name": name,
            "retry_options": retry_options,
            "input": input_,
            "instance_id": instance_id,
        }
        self.sub_calls.append(call)
        return ("sub", instance_id)

    def task_all(self, tasks):
        copied = list(tasks)
        self.task_all_calls.append(copied)
        return ("all", copied)


class _CustomExecutor(DurableFlowExecutor):
    def __init__(self) -> None:
        self.call: tuple[Any, dict[str, Any] | None, str | None] | None = None

    async def start(
        self,
        flow: Any,
        *,
        inputs: dict[str, Any] | None = None,
        instance_id: str | None = None,
    ) -> str:
        self.call = (flow, inputs, instance_id)
        return "custom-result"


async def run_scenario() -> None:
    # Public single-flow executor: custom parent ID and retry policy reach start_new.
    client = _RecordingClient()
    policy = DurableRetryPolicy(
        attempts=4, initial_delay_seconds=0.25, backoff=1.5, jitter=0.1
    )
    single = DurableFunctionsExecutor(client, retry_policy=policy)
    started = await single.start(
        str(_FLOW), inputs={"message": "hello"}, instance_id="parent-42"
    )
    assert started == "parent-42"
    call = client.calls[-1]
    assert call["orchestration_function_name"] == FLOW_ORCHESTRATOR
    assert call["instance_id"] == "parent-42"
    assert call["client_input"] == {
        "flow_name": str(_FLOW),
        "inputs": {"message": "hello"},
        "retry_policy": policy.to_dict(),
    }

    # The actual DAG orchestrator derives deterministic child IDs and threads the
    # per-node retry policy into every node-orchestrator payload.
    context = _DagContext()
    dag_orchestrator = _DagOrchestrator(context, retry_policy=policy.to_dict())
    run = dag_orchestrator.run(
        str(_FLOW), inputs={"message": "hello"}, instance_id="parent-42"
    )
    task_all_marker = next(run)
    assert task_all_marker == (
        "all",
        [("sub", "parent-42_step_a"), ("sub", "parent-42_step_b")],
    )
    assert [c["instance_id"] for c in context.sub_calls] == [
        "parent-42_step_a",
        "parent-42_step_b",
    ]
    assert all(c["input"]["retry_policy"] == policy.to_dict() for c in context.sub_calls)
    try:
        run.send(["result-a", "result-b"])
    except StopIteration as stop:
        assert stop.value == {"step_a": "result-a", "step_b": "result-b"}
    else:
        raise AssertionError("DAG orchestrator did not finish after task_all")

    # Both group executors serialize the same plan contract and select their own
    # registered orchestrator.
    plan = DurableFlowPlan(
        [DurableFlowStep(flow_name="flows/echo", name="echo")]
    )
    for executor_type, orchestrator_name in (
        (DurableSequenceExecutor, SEQUENCE_ORCHESTRATOR),
        (DurableParallelExecutor, PARALLEL_ORCHESTRATOR),
    ):
        group_client = _RecordingClient()
        executor = executor_type(group_client, retry_policy=policy)
        result = await executor.start(
            plan, inputs={"shared": "S"}, instance_id=f"id-{orchestrator_name}"
        )
        assert result == f"id-{orchestrator_name}"
        group_call = group_client.calls[-1]
        assert group_call["orchestration_function_name"] == orchestrator_name
        assert group_call["client_input"] == {
            **plan.to_dict(),
            "base_inputs": {"shared": "S"},
            "retry_policy": policy.to_dict(),
        }

        try:
            await executor.start("not-a-plan")
        except TypeError as exc:
            assert "requires a DurableFlowPlan" in str(exc)
        else:
            raise AssertionError("group executor accepted a non-DurableFlowPlan")

    # Custom executors are a real extension seam: run_durable_flow delegates without
    # interpreting the flow or changing the caller's inputs/instance ID.
    custom = _CustomExecutor()
    custom_result = await run_durable_flow(
        {"virtual": "flow"},
        executor=custom,
        inputs={"x": 1},
        instance_id="custom-id",
    )
    assert custom_result == "custom-result"
    assert custom.call == ({"virtual": "flow"}, {"x": 1}, "custom-id")
