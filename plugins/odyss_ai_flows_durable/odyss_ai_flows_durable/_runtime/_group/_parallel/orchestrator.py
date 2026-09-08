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
# Parallel orchestration
# ---------------------------------------------------------

def run_parallel_orchestration(
    context: df.DurableOrchestrationContext,
) -> DurableGenerator[dict[str, Any]]:
    raw = context.get_input() or {}
    steps = [DurableFlowStep.from_dict(s) for s in raw.get("steps", [])]
    base_inputs: dict[str, Any] = dict(raw.get("base_inputs") or {})

    retry_policy_data = raw.get("retry_policy")
    retry_policy = DurableRetryPolicy.from_dict(retry_policy_data) if retry_policy_data else None

    scheduled: list[tuple[DurableFlowStep, DurableTask]] = [
        (step, schedule_step(context, step, base_inputs))
        for step in steps
    ]

    if not scheduled:
        return {"flow_results": {}}

    results: list[Any] = [None] * len(scheduled)

    if retry_policy is None:
        parallel_results = yield context.task_all([task for _, task in scheduled])
        results = list(parallel_results)
    else:
        results = yield from _run_parallel_with_retry(
            context=context,
            scheduled=scheduled,
            base_inputs=base_inputs,
            retry_policy=retry_policy,
        )

    flow_results: dict[str, Any] = {}
    subflow_tasks: list[tuple[str, DurableTask]] = []

    for (step, _), result in zip(scheduled, results):
        key = step.name or step.flow_name
        flow_results[key] = result

        nested_groups = extract_subflow_groups(result)
        if nested_groups:
            subflow_tasks.append((
                key,
                context.call_sub_orchestrator(
                    SUBFLOWS_ORCHESTRATOR,
                    {
                        "groups": [g.to_dict() for g in nested_groups],
                        "base_inputs": base_inputs,
                        "_ancestor_flow_names": [s.flow_name for s in steps],
                    },
                ),
            ))

    if subflow_tasks:
        subflow_results = yield context.task_all(
            [task for _, task in subflow_tasks]
        )

        for (key, _), subflow_result in zip(subflow_tasks, subflow_results):
            if isinstance(subflow_result, dict):
                existing = flow_results[key]
                flow_results[key] = {
                    **(existing if isinstance(existing, dict) else {}),
                    "subflow_results": subflow_result.get("subflow_results", {}),
                }

    return {"flow_results": flow_results}


# ---------------------------------------------------------
# Internal
# ---------------------------------------------------------

def _run_parallel_with_retry(
    *,
    context: df.DurableOrchestrationContext,
    scheduled: list[tuple[DurableFlowStep, DurableTask]],
    base_inputs: dict[str, Any],
    retry_policy: DurableRetryPolicy,
) -> DurableGenerator[list[Any]]:
    results: list[Any] = [None] * len(scheduled)

    try:
        parallel_results = yield context.task_all([task for _, task in scheduled])
        results = list(parallel_results)
    except Exception:
        for i, (_, task) in enumerate(scheduled):
            try:
                results[i] = yield task
            except Exception as exc:
                results[i] = exc

    failures = [i for i, r in enumerate(results) if isinstance(r, Exception)]

    for attempt in range(1, retry_policy.attempts):
        if not failures:
            break

        delay = retry_policy.initial_delay_seconds * (retry_policy.backoff ** (attempt - 1))

        if retry_policy.jitter > 0:
            jitter_factor = yield context.call_activity(
                JITTER_ACTIVITY,
                retry_policy.jitter,
            )
            delay *= 1.0 + float(jitter_factor)

        fire_at = context.current_utc_datetime + datetime.timedelta(seconds=delay)
        yield context.create_timer(fire_at)

        retry_tasks: list[tuple[int, DurableTask]] = [
            (i, schedule_step(context, scheduled[i][0], base_inputs))
            for i in failures
        ]

        try:
            retry_results = yield context.task_all([t for _, t in retry_tasks])
            for pos, (i, _) in enumerate(retry_tasks):
                results[i] = retry_results[pos]
        except Exception:
            for i, task in retry_tasks:
                try:
                    results[i] = yield task
                except Exception as exc:
                    results[i] = exc

        failures = [i for i in failures if isinstance(results[i], Exception)]

    if failures:
        raise results[failures[0]]

    return results
