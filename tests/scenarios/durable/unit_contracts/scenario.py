from __future__ import annotations

from odyss_ai_flows_durable import (
    DispatchMode,
    DurableFlowPlan,
    DurableFlowStep,
    DurableRetryPolicy,
    DurableSubflowGroup,
    DurableSubflowGroupConfig,
    DurableSubflowOutput,
    FlowOrchestrationInput,
)
from odyss_ai_flows_durable._contracts.naming import (
    build_child_instance_id,
    dependency_event_name,
)
from odyss_ai_flows_durable._contracts.payloads import (
    NodeActivityInput,
    NodeOrchestrationInput,
    SignalActivityInput,
)


async def run_scenario() -> None:
    # === Serialization round-trips (dataclasses -> value equality) =============
    step = DurableFlowStep(
        flow_name="flows/echo", mode=DispatchMode.DIRECT, name="s1",
        inputs={"message": "hi"}, input_keys=["message"], output_keys=["echo"],
    )
    assert DurableFlowStep.from_dict(step.to_dict()) == step

    plan = DurableFlowPlan([step, DurableFlowStep(flow_name="flows/echo")])
    assert DurableFlowPlan.from_dict(plan.to_dict()).to_dict() == plan.to_dict()

    cfg = DurableSubflowGroupConfig(max_concurrent=2, wait_before_seconds=1.5, skip_group_output=True)
    assert DurableSubflowGroupConfig.from_dict(cfg.to_dict()) == cfg

    group = DurableSubflowGroup(key="fetch", steps=[step], config=cfg)
    assert DurableSubflowGroup.from_dict(group.to_dict()) == group

    flat = DurableSubflowOutput(data={"n": 1}, subflows=[step])
    grouped = DurableSubflowOutput(data={"n": 2}, groups=[group], default_group_config=cfg)
    assert DurableSubflowOutput.from_dict(flat.to_dict()) == flat
    assert DurableSubflowOutput.from_dict(grouped.to_dict()) == grouped

    # to_dict omits empty subflows/groups and a None default config; from_dict restores them.
    minimal = DurableSubflowOutput(data={"n": 3})
    assert minimal.to_dict() == {"_type": "DurableSubflowOutput", "data": {"n": 3}}
    assert DurableSubflowOutput.from_dict(minimal.to_dict()) == minimal

    # payloads.py round-trip via from_mapping (not from_dict).
    foi = FlowOrchestrationInput(flow_name="flows/echo", inputs={"a": 1}, retry_policy={"attempts": 2})
    assert FlowOrchestrationInput.from_mapping(foi.to_dict()) == foi
    noi = NodeOrchestrationInput(
        node="consumer", flow_name="flows/echo", base_inputs={"a": 1},
        upstream=["producer"], downstream_instance_ids={"consumer": "id_c"},
    )
    assert NodeOrchestrationInput.from_mapping(noi.to_dict()) == noi
    nai = NodeActivityInput(node="consumer", flow_name="flows/echo", base_inputs={"a": 1}, dep_results={"producer": "p"})
    assert NodeActivityInput.from_mapping(nai.to_dict()) == nai
    sai = SignalActivityInput(target_instance_id="id_c", event_name="dep:consumer", data={"r": 1})
    assert SignalActivityInput.from_mapping(sai.to_dict()) == sai

    # === CHARACTERIZATION (§4.1): output_keys / input_keys default asymmetry ====
    # output_keys and input_keys have OPPOSITE defaults, and from_dict maps an *absent*
    # output_keys differently from an *explicit null* — three behaviors for one field.
    # output_keys gates forward propagation ([] = nothing, None = whole result).
    assert DurableFlowStep(flow_name="f").output_keys == []          # direct default: []
    assert DurableFlowStep(flow_name="f").input_keys is None          # direct default: None
    absent = DurableFlowStep.from_dict({"flow_name": "f"})
    assert absent.output_keys == [] and absent.input_keys is None     # absent -> [] / None
    explicit_null = DurableFlowStep.from_dict({"flow_name": "f", "output_keys": None, "input_keys": None})
    assert explicit_null.output_keys is None                          # explicit null -> None (diverges!)
    assert absent.output_keys != explicit_null.output_keys            # the load-bearing divergence
    empty = DurableFlowStep.from_dict({"flow_name": "f", "output_keys": [], "input_keys": []})
    assert empty.output_keys == [] and empty.input_keys == []

    # === DurableSubflowGroupConfig.resolved(): explicit -> default -> hard default
    hard = DurableSubflowGroupConfig().resolved()
    assert (hard.max_concurrent, hard.wait_before_seconds, hard.wait_after_seconds, hard.skip_group_output) \
        == (None, 0.0, 0.0, False)
    explicit = DurableSubflowGroupConfig(max_concurrent=3, wait_before_seconds=2.0, skip_group_output=True)
    r = explicit.resolved(DurableSubflowGroupConfig(max_concurrent=99, skip_group_output=False))
    assert (r.max_concurrent, r.wait_before_seconds, r.skip_group_output) == (3, 2.0, True)  # explicit wins
    defaults = DurableSubflowGroupConfig(max_concurrent=5, wait_after_seconds=4.0, skip_group_output=True)
    r2 = DurableSubflowGroupConfig().resolved(defaults)
    assert (r2.max_concurrent, r2.wait_after_seconds, r2.skip_group_output, r2.wait_before_seconds) \
        == (5, 4.0, True, 0.0)  # unset falls to default, then hard default

    # is_serialized: only a dict tagged _type == "DurableSubflowOutput".
    assert DurableSubflowOutput.is_serialized(flat.to_dict()) is True
    assert DurableSubflowOutput.is_serialized({"_type": "other"}) is False
    assert DurableSubflowOutput.is_serialized("not a dict") is False

    # === DurableRetryPolicy: defaults, typed round-trip, coercion ===============
    p = DurableRetryPolicy()
    assert (p.attempts, p.backoff, p.jitter, p.initial_delay_seconds) == (3, 2.0, 0.0, 1.0)
    assert DurableRetryPolicy.from_dict(p.to_dict()) == p
    coerced = DurableRetryPolicy.from_dict({"attempts": "4", "backoff": "1.5"})
    assert coerced.attempts == 4 and coerced.backoff == 1.5

    # === naming: event names + CHARACTERIZATION (§5) instance-id collision ======
    assert dependency_event_name("consumer") == "dep:consumer"
    assert build_child_instance_id(parent_instance_id="root", node="consumer") == "root_consumer"
    assert build_child_instance_id(parent_instance_id=None, node="consumer") == "consumer"
    # "_" is an ambiguous separator: two different (parent, node) pairs collide.
    a = build_child_instance_id(parent_instance_id="foo", node="bar_baz")
    b = build_child_instance_id(parent_instance_id="foo_bar", node="baz")
    assert a == b == "foo_bar_baz", (a, b)
