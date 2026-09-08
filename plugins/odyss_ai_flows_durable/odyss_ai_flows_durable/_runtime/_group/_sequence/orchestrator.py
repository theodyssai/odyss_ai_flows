from __future__ import annotations

import datetime
from typing import Any

import azure.durable_functions as df

from odyss_ai_flows_durable._contracts.constants import (
    JITTER_ACTIVITY,
    SUBFLOWS_ORCHESTRATOR,
)

from odyss_ai_flows_durable._contracts.flows import (
    DurableFlowStep,
)

from odyss_ai_flows_durable._contracts.retry import (
    DurableRetryPolicy,
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
# Sequence orchestration
# ---------------------------------------------------------

def run_sequence_orchestration(
    context: df.DurableOrchestrationContext,
) -> DurableGenerator[dict[str, Any]]:
    raw = context.get_input() or {}
    steps = [DurableFlowStep.from_dict(s) for s in raw.get("steps", [])]
    base_inputs: dict[str, Any] = dict(raw.get("base_inputs") or {})

    retry_policy_data = raw.get("retry_policy")
    retry_policy = DurableRetryPolicy.from_dict(retry_policy_data) if retry_policy_data else None

    flow_results: dict[str, Any] = {}

    all_flow_names = [s.flow_name for s in steps]

    for step in steps:
        if retry_policy is not None:
            result = yield from _run_step_with_retry(
                context, step, base_inputs, retry_policy,
                ancestor_flow_names=all_flow_names,
            )
        else:
            result = yield from _run_step(
                context, step, base_inputs, ancestor_flow_names=all_flow_names
            )

        result_key = step.name or step.flow_name
        flow_results[result_key] = result

        if isinstance(result, dict):
            propagated = (
                {k: result[k] for k in step.output_keys if k in result}
                if step.output_keys is not None
                else result
            )
            base_inputs = merge(base_inputs, propagated)

    return {"flow_results": flow_results}


# ---------------------------------------------------------
# Internal
# ---------------------------------------------------------

def _run_step_with_retry(
    context: df.DurableOrchestrationContext,
    step: DurableFlowStep,
    base_inputs: dict[str, Any],
    retry_policy: DurableRetryPolicy,
    *,
    ancestor_flow_names: list[str],
) -> DurableGenerator[Any]:
    for attempt in range(retry_policy.attempts):
        if attempt > 0:
            delay = retry_policy.initial_delay_seconds * (retry_policy.backoff ** (attempt - 1))

            if retry_policy.jitter > 0:
                jitter_factor = yield context.call_activity(
                    JITTER_ACTIVITY,
                    retry_policy.jitter,
                )
                delay *= 1.0 + float(jitter_factor)

            fire_at = context.current_utc_datetime + datetime.timedelta(seconds=delay)
            yield context.create_timer(fire_at)

        try:
            return (yield from _run_step(
                context, step, base_inputs, ancestor_flow_names=ancestor_flow_names
            ))
        except Exception:
            if attempt == retry_policy.attempts - 1:
                raise


def _run_step(
    context: df.DurableOrchestrationContext,
    step: DurableFlowStep,
    base_inputs: dict[str, Any],
    *,
    ancestor_flow_names: list[str],
) -> DurableGenerator[Any]:
    task: DurableTask = schedule_step(context, step, base_inputs)
    result = yield task

    nested_groups = extract_subflow_groups(result)
    if not nested_groups:
        return result

    subflow_result = yield context.call_sub_orchestrator(
        SUBFLOWS_ORCHESTRATOR,
        {
            "groups": [g.to_dict() for g in nested_groups],
            "base_inputs": merge(
                base_inputs,
                result if isinstance(result, dict) else {},
            ),
            "_ancestor_flow_names": ancestor_flow_names,
        },
    )

    if isinstance(result, dict) and isinstance(subflow_result, dict):
        return {
            **result,
            "subflow_results": subflow_result.get("subflow_results", {}),
        }

    return result
