from __future__ import annotations

import datetime
from typing import Any

from odyss_ai_flows_durable import DispatchMode, DurableFlowStep, DurableRetryPolicy
from odyss_ai_flows_durable._contracts.constants import (
    DIRECT_FLOW_ACTIVITY,
    JITTER_ACTIVITY,
)
from odyss_ai_flows_durable._contracts.payloads import NodeActivityInput
from odyss_ai_flows_durable._runtime._group._sequence.orchestrator import (
    _run_step_with_retry,
)
from odyss_ai_flows_durable._runtime._single.handlers import _run_with_retry_policy


class _Context:
    def __init__(self) -> None:
        self.current_utc_datetime = datetime.datetime(
            2026, 7, 23, 12, 0, tzinfo=datetime.timezone.utc
        )
        self.activity_calls: list[tuple[str, Any]] = []
        self.timers: list[datetime.datetime] = []

    def call_activity(self, name, input_data):
        self.activity_calls.append((name, input_data))
        return ("activity", name, len(self.activity_calls))

    def create_timer(self, fire_at):
        self.timers.append(fire_at)
        return ("timer", fire_at)


def _finish(generator, value):
    try:
        generator.send(value)
    except StopIteration as stop:
        return stop.value
    raise AssertionError("retry generator did not finish")


async def run_scenario() -> None:
    # Sequence retry uses exponential delays and draws jitter through an Activity,
    # keeping randomness out of replayed orchestrator code.
    sequence_context = _Context()
    sequence_policy = DurableRetryPolicy(
        attempts=3,
        initial_delay_seconds=2.0,
        backoff=3.0,
        jitter=0.5,
    )
    step = DurableFlowStep(
        flow_name="flows/echo",
        mode=DispatchMode.DIRECT,
        inputs={"message": "hello"},
    )
    sequence = _run_step_with_retry(
        sequence_context, step, {"shared": "S"}, sequence_policy, ancestor_flow_names=[]
    )

    first = next(sequence)
    assert first[1] == DIRECT_FLOW_ACTIVITY

    jitter_1 = sequence.throw(RuntimeError("attempt 1"))
    assert jitter_1[1] == JITTER_ACTIVITY
    timer_1 = sequence.send(0.25)
    assert timer_1 == (
        "timer",
        sequence_context.current_utc_datetime
        + datetime.timedelta(seconds=2.0 * 1.25),
    )
    second = sequence.send(None)
    assert second[1] == DIRECT_FLOW_ACTIVITY

    jitter_2 = sequence.throw(RuntimeError("attempt 2"))
    assert jitter_2[1] == JITTER_ACTIVITY
    timer_2 = sequence.send(0.5)
    assert timer_2 == (
        "timer",
        sequence_context.current_utc_datetime
        + datetime.timedelta(seconds=(2.0 * 3.0) * 1.5),
    )
    third = sequence.send(None)
    assert third[1] == DIRECT_FLOW_ACTIVITY
    assert _finish(sequence, {"echo": "hello"}) == {"echo": "hello"}
    assert [name for name, _ in sequence_context.activity_calls] == [
        DIRECT_FLOW_ACTIVITY,
        JITTER_ACTIVITY,
        DIRECT_FLOW_ACTIVITY,
        JITTER_ACTIVITY,
        DIRECT_FLOW_ACTIVITY,
    ]

    # With jitter disabled, single-node retry goes straight from a failure to a
    # durable timer; no jitter Activity is scheduled.
    single_context = _Context()
    single_policy = DurableRetryPolicy(
        attempts=2,
        initial_delay_seconds=1.5,
        backoff=10.0,
        jitter=0.0,
    )
    activity_input = NodeActivityInput(
        node="node",
        flow_name="flow",
        base_inputs={},
        dep_results={},
    )
    single = _run_with_retry_policy(
        context=single_context,
        activity_name="node_activity",
        activity_input=activity_input,
        retry_policy=single_policy,
    )
    assert next(single)[1] == "node_activity"
    timer = single.throw(RuntimeError("first failure"))
    assert timer == (
        "timer",
        single_context.current_utc_datetime + datetime.timedelta(seconds=1.5),
    )
    assert single.send(None)[1] == "node_activity"
    assert _finish(single, "recovered") == "recovered"
    assert all(name != JITTER_ACTIVITY for name, _ in single_context.activity_calls)

    # Exhaustion re-raises the last underlying exception instead of wrapping it.
    exhausted_context = _Context()
    exhausted = _run_with_retry_policy(
        context=exhausted_context,
        activity_name="node_activity",
        activity_input=activity_input,
        retry_policy=DurableRetryPolicy(
            attempts=2,
            initial_delay_seconds=0.0,
            backoff=1.0,
        ),
    )
    next(exhausted)
    exhausted.throw(RuntimeError("first"))
    exhausted.send(None)
    try:
        exhausted.throw(ValueError("final failure"))
    except ValueError as exc:
        assert str(exc) == "final failure"
    else:
        raise AssertionError("retry exhaustion did not preserve the final exception")
