from __future__ import annotations

import datetime
from typing import Any

import azure.durable_functions as df

from odyss_ai_flows_durable._contracts.constants import (
    SUBFLOWS_ORCHESTRATOR,
    VIRTUAL_SPAN_ACTIVITY,
)

from odyss_ai_flows_durable._contracts.cycle_detection import (
    warn_if_subflow_cycle,
)

from odyss_ai_flows_durable._contracts.flows import (
    DurableSubflowGroup,
)

from odyss_ai_flows_durable._contracts.types import (
    DurableGenerator,
    DurableTask,
)

from odyss_ai_flows_durable._runtime._group.utils import (
    extract_subflow_groups,
    merge,
    schedule_step,
)


# ---------------------------------------------------------
# Subflows orchestration (staged groups, each group internally batched)
# ---------------------------------------------------------

def run_subflows_orchestration(
    context: df.DurableOrchestrationContext,
) -> DurableGenerator[dict[str, Any]]:
    raw = context.get_input() or {}
    groups = [DurableSubflowGroup.from_dict(g) for g in raw.get("groups", [])]
    base_inputs: dict[str, Any] = dict(raw.get("base_inputs") or {})
    ancestor_flows: set[str] = set(raw.get("_ancestor_flow_names", []))

    base_inputs = yield from _build_virtual_parent_inputs(context, base_inputs)

    if not groups:
        return {"subflow_results": {}}

    subflow_results: dict[str, Any] = {}
    nested_specs: list[tuple[str, str, Any, dict[str, Any], set[str]]] = []
    running_inputs = base_inputs

    for group in groups:
        group_inputs = yield from _build_virtual_group_inputs(context, running_inputs, group)

        group_results, group_running_inputs = yield from _run_group(
            context, group, group_inputs, ancestor_flows=ancestor_flows
        )

        subflow_results[group.key] = group_results

        group_ancestor_flows = ancestor_flows | {s.flow_name for s in group.steps}

        for step_key, result in group_results.items():
            if extract_subflow_groups(result):
                nested_specs.append((group.key, step_key, result, group_running_inputs, group_ancestor_flows))

        if not group.config.skip_group_output:
            running_inputs = group_running_inputs

    if nested_specs:
        nested_tasks: list[DurableTask] = [
            context.call_sub_orchestrator(
                SUBFLOWS_ORCHESTRATOR,
                {
                    "groups": [g.to_dict() for g in extract_subflow_groups(result)],
                    "base_inputs": merge(
                        spec_inputs,
                        result if isinstance(result, dict) else {},
                    ),
                    "_ancestor_flow_names": sorted(group_ancestor_flows),
                },
            )
            for _, _, result, spec_inputs, group_ancestor_flows in nested_specs
        ]

        nested_results = yield context.task_all(nested_tasks)

        for (group_key, step_key, _, _, _), nested_result in zip(nested_specs, nested_results):
            if isinstance(nested_result, dict):
                existing = subflow_results[group_key][step_key]
                subflow_results[group_key][step_key] = {
                    **(existing if isinstance(existing, dict) else {}),
                    "subflow_results": nested_result.get("subflow_results", {}),
                }

    return {"subflow_results": subflow_results}


# ---------------------------------------------------------
# Internal: one staged group
# ---------------------------------------------------------

def _run_group(
    context: df.DurableOrchestrationContext,
    group: DurableSubflowGroup,
    base_inputs: dict[str, Any],
    *,
    ancestor_flows: set[str],
) -> DurableGenerator[tuple[dict[str, Any], dict[str, Any]]]:
    config = group.config

    if config.wait_before_seconds:
        yield context.create_timer(
            context.current_utc_datetime + datetime.timedelta(seconds=config.wait_before_seconds)
        )

    batch_size = (
        config.max_concurrent
        if config.max_concurrent and config.max_concurrent > 0
        else len(group.steps)
    )
    batch_size = max(batch_size, 1)

    running_inputs = base_inputs
    group_results: dict[str, Any] = {}

    for batch_start in range(0, len(group.steps), batch_size):
        batch = group.steps[batch_start:batch_start + batch_size]

        batch_tasks: list[DurableTask] = []
        for step in batch:
            warn_if_subflow_cycle(step.flow_name, ancestor_flows)
            batch_tasks.append(schedule_step(context, step, running_inputs))

        batch_results = yield context.task_all(batch_tasks)

        for step, result in zip(batch, batch_results):
            key = step.name or step.flow_name
            group_results[key] = result

            if isinstance(result, dict):
                propagated = (
                    {k: result[k] for k in step.output_keys if k in result}
                    if step.output_keys is not None
                    else result
                )
                running_inputs = merge(running_inputs, propagated)

    if config.wait_after_seconds:
        yield context.create_timer(
            context.current_utc_datetime + datetime.timedelta(seconds=config.wait_after_seconds)
        )

    return group_results, running_inputs


# ---------------------------------------------------------
# Internal: telemetry
# ---------------------------------------------------------

def _build_virtual_parent_inputs(
    context: df.DurableOrchestrationContext,
    base_inputs: dict[str, Any],
) -> DurableGenerator[dict[str, Any]]:
    current_traceparent = base_inputs.get("_traceparent")
    current_depth = base_inputs.get("_subflows_depth", 0)

    virtual = yield context.call_activity(
        VIRTUAL_SPAN_ACTIVITY,
        {
            "_traceparent": current_traceparent,
            "span_name": f"durable.subflows_level:{current_depth}",
            "attributes": {
                "durable.instance_id": base_inputs.get("instance_id"),
                "durable.subflows_depth": current_depth,
            },
        },
    )

    level_traceparent = virtual.get("traceparent", current_traceparent)
    level_base_inputs = dict(base_inputs)

    if level_traceparent:
        level_base_inputs["_traceparent"] = level_traceparent

    level_base_inputs["_subflows_depth"] = current_depth + 1

    return level_base_inputs


def _build_virtual_group_inputs(
    context: df.DurableOrchestrationContext,
    base_inputs: dict[str, Any],
    group: DurableSubflowGroup,
) -> DurableGenerator[dict[str, Any]]:
    current_traceparent = base_inputs.get("_traceparent")
    current_depth = base_inputs.get("_subflows_depth", 0)

    virtual = yield context.call_activity(
        VIRTUAL_SPAN_ACTIVITY,
        {
            "_traceparent": current_traceparent,
            "span_name": f"durable.subflows_level:{current_depth}.group:{group.key}",
            "attributes": {
                "durable.instance_id": base_inputs.get("instance_id"),
                "durable.subflows_depth": current_depth,
                "durable.subflows_group": group.key,
                "durable.subflows_group_size": len(group.steps),
            },
        },
    )

    level_traceparent = virtual.get("traceparent", current_traceparent)
    group_inputs = dict(base_inputs)

    if level_traceparent:
        group_inputs["_traceparent"] = level_traceparent

    return group_inputs
