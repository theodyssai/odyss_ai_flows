from __future__ import annotations

from odyss_ai_flows_durable import (
    DispatchMode,
    DurableFlowStep,
    DurableSubflowGroup,
    DurableSubflowGroupConfig,
    DurableSubflowOutput,
)
from odyss_ai_flows_durable._contracts.constants import (
    DIRECT_FLOW_ACTIVITY,
    FLOW_ORCHESTRATOR,
)
from odyss_ai_flows_durable._runtime._group._subflows.orchestrator import (
    _run_group,
)
from odyss_ai_flows_durable._runtime._group.utils import (
    DEFAULT_SUBFLOW_GROUP_KEY,
    extract_subflow_groups,
    merge,
    schedule_step,
)


class _StubContext:
    """Records call_activity / call_sub_orchestrator invocations, no Durable runtime."""

    def __init__(self) -> None:
        self.activity_calls: list = []
        self.sub_orchestrator_calls: list = []
        self.task_all_calls: list = []

    def call_activity(self, name, input_data):
        self.activity_calls.append((name, input_data))
        return ("activity", name, len(self.activity_calls))

    def call_sub_orchestrator(self, name, input_data, *args, **kwargs):
        self.sub_orchestrator_calls.append((name, input_data, args, kwargs))
        return ("sub", name)

    def task_all(self, tasks):
        copied = list(tasks)
        self.task_all_calls.append(copied)
        return ("all", copied)


async def run_scenario() -> None:
    # --- merge: deep-merges dicts, replaces scalars/lists, never mutates inputs ---
    base = {"a": {"x": 1, "y": 2}, "list": [1, 2], "scalar": "old"}
    update = {"a": {"y": 20, "z": 3}, "list": [9], "scalar": "new"}
    assert merge(base, update) == {"a": {"x": 1, "y": 20, "z": 3}, "list": [9], "scalar": "new"}
    assert base == {"a": {"x": 1, "y": 2}, "list": [1, 2], "scalar": "old"}   # unmutated

    # --- extract_subflow_groups ------------------------------------------------
    assert extract_subflow_groups("not a dict") == []
    assert extract_subflow_groups({"k": 1}) == []               # nothing serialized

    flat = DurableSubflowOutput(data={}, subflows=[DurableFlowStep(flow_name="f")])
    groups = extract_subflow_groups({"router": flat.to_dict()})
    assert [g.key for g in groups] == [DEFAULT_SUBFLOW_GROUP_KEY]  # flat list -> one "__default__" group
    assert len(groups[0].steps) == 1

    # A serialized output that carries no subflows/groups yields nothing.
    assert extract_subflow_groups({"router": DurableSubflowOutput(data={}).to_dict()}) == []

    grouped = DurableSubflowOutput(
        data={},
        groups=[DurableSubflowGroup(
            key="fetch", steps=[DurableFlowStep(flow_name="f")],
            config=DurableSubflowGroupConfig(max_concurrent=2),
        )],
    )
    g2 = extract_subflow_groups({"router": grouped.to_dict()})
    assert [g.key for g in g2] == ["fetch"]
    assert g2[0].config.max_concurrent == 2

    # --- schedule_step: input_keys filtering -----------------------------------
    ctx = _StubContext()
    schedule_step(ctx, DurableFlowStep(flow_name="f", input_keys=["keep"], inputs={"own": 1}),
                  {"keep": "K", "drop": "D"})
    assert ctx.sub_orchestrator_calls[0][1]["inputs"] == {"keep": "K", "own": 1}  # "drop" filtered

    ctx_all = _StubContext()
    schedule_step(ctx_all, DurableFlowStep(flow_name="f"), {"a": 1, "b": 2})
    assert ctx_all.sub_orchestrator_calls[0][1]["inputs"] == {"a": 1, "b": 2}     # input_keys=None -> all

    # --- CHARACTERIZATION (§4.2 / §4.3): a DURABLE step is dispatched with NO
    #     retry_policy threaded in and NO instance_id — so a step-level DurableRetryPolicy
    #     never reaches subflow steps, and each retry re-runs the whole flow fresh. -------
    ctx_dur = _StubContext()
    schedule_step(ctx_dur, DurableFlowStep(flow_name="f", mode=DispatchMode.DURABLE), {})
    name, payload, args, kwargs = ctx_dur.sub_orchestrator_calls[0]
    assert name == FLOW_ORCHESTRATOR
    assert payload["retry_policy"] is None       # §4.2: policy not threaded through
    assert args == () and kwargs == {}           # §4.3: no instance_id -> no memoization on retry

    # A DIRECT step is dispatched to the direct-flow activity instead.
    ctx_dir = _StubContext()
    schedule_step(ctx_dir, DurableFlowStep(flow_name="f", mode=DispatchMode.DIRECT), {})
    assert ctx_dir.activity_calls[0][0] == DIRECT_FLOW_ACTIVITY
    assert ctx_dir.sub_orchestrator_calls == []

    # --- _run_group: max_concurrent=2 schedules exact 2-then-1 batches -----------
    # Drive the replay-safe generator directly so batching/order are deterministic
    # and do not depend on Azurite wall-clock behavior.
    batch_ctx = _StubContext()
    batch_group = DurableSubflowGroup(
        key="fetch",
        steps=[
            DurableFlowStep(
                flow_name=f"flow_{label}",
                name=label,
                mode=DispatchMode.DIRECT,
                inputs={"label": label},
                output_keys=["value"],
            )
            for label in ("a", "b", "c")
        ],
        config=DurableSubflowGroupConfig(max_concurrent=2),
    )
    batch_run = _run_group(
        batch_ctx,
        batch_group,
        {"shared": "S"},
        ancestor_flows=set(),
    )

    first_batch = next(batch_run)
    assert first_batch == ("all", [
        ("activity", DIRECT_FLOW_ACTIVITY, 1),
        ("activity", DIRECT_FLOW_ACTIVITY, 2),
    ])
    assert [
        call[1]["flow_name"] for call in batch_ctx.activity_calls
    ] == ["flow_a", "flow_b"]

    second_batch = batch_run.send([{"value": "a"}, {"value": "b"}])
    assert second_batch == ("all", [
        ("activity", DIRECT_FLOW_ACTIVITY, 3),
    ])
    assert batch_ctx.activity_calls[2][1] == {
        "flow_name": "flow_c",
        "base_inputs": {
            "shared": "S",
            "value": "b",
            "label": "c",
        },
    }

    try:
        batch_run.send([{"value": "c"}])
    except StopIteration as stop:
        group_results, running_inputs = stop.value
    else:
        raise AssertionError("subflow group did not finish after its second batch")

    assert list(group_results) == ["a", "b", "c"]
    assert running_inputs == {"shared": "S", "value": "c"}
