from __future__ import annotations

import datetime
from typing import Any

import azure.durable_functions as df
from opentelemetry.trace import SpanKind

from odyss_ai_flows import run_flow

from odyss_ai_flows_durable._contracts.constants import (
    JITTER_ACTIVITY,
)

from odyss_ai_flows_durable._contracts.naming import (
    dependency_event_name,
)

from odyss_ai_flows_durable._contracts.payloads import (
    NodeActivityInput,
    NodeOrchestrationInput,
    SignalActivityInput,
)

from odyss_ai_flows_durable._contracts.protocols import (
    DurableEventClient,
)

from odyss_ai_flows_durable._contracts.retry import (
    DurableRetryPolicy,
)

from odyss_ai_flows_durable._contracts.types import (
    DurableGenerator,
    DurableTask,
)

from odyss_ai_flows_durable._telemetry import (
    get_tracer,
    is_telemetry_enabled,
    propagator,
)


# ---------------------------------------------------------
# Orchestration
# ---------------------------------------------------------

def run_node_orchestration(
    context: df.DurableOrchestrationContext,
    *,
    activity_name: str,
    signal_activity_name: str,
    retry_options: df.RetryOptions | None = None,
) -> DurableGenerator[Any]:
    resolved_retry_options = (
        retry_options or df.RetryOptions(5_000, 3)
    )

    orchestration_input = _read_orchestration_input(context)

    retry_policy = (
        DurableRetryPolicy.from_dict(orchestration_input.retry_policy)
        if orchestration_input.retry_policy
        else None
    )

    dependency_results = yield from _wait_for_dependency_results(
        context=context,
        upstream_nodes=orchestration_input.upstream,
    )

    node_result = yield from _run_node_activity(
        context=context,
        activity_name=activity_name,
        retry_options=resolved_retry_options,
        retry_policy=retry_policy,
        orchestration_input=orchestration_input,
        dependency_results=dependency_results,
    )

    yield from _signal_downstream_nodes(
        context=context,
        signal_activity_name=signal_activity_name,
        retry_options=resolved_retry_options,
        orchestration_input=orchestration_input,
        node_result=node_result,
    )

    return node_result


# ---------------------------------------------------------
# Activities
# ---------------------------------------------------------

async def run_node_activity(input_data: dict[str, Any]) -> Any:
    activity_input = NodeActivityInput.from_mapping(input_data)

    if not await is_telemetry_enabled():
        return await _run_node_core(activity_input)

    traceparent = (activity_input.base_inputs or {}).get("_traceparent")
    parent_ctx = propagator.extract({"traceparent": traceparent}) if traceparent else None
    span_name = f"durable.activity:node:{activity_input.flow_name}:{activity_input.node}"

    with get_tracer(__name__).start_as_current_span(span_name, context=parent_ctx, kind=SpanKind.INTERNAL) as span:
        span.set_attribute("durable.node", activity_input.node)
        span.set_attribute("durable.flow_name", activity_input.flow_name)
        try:
            return await _run_node_core(activity_input)
        except Exception as exc:
            span.record_exception(exc)
            span.set_attribute("durable.error", str(exc))
            raise


async def _run_node_core(activity_input: NodeActivityInput) -> Any:
    task = run_flow(
        activity_input.flow_name,
        inputs=activity_input.base_inputs,
        target_node=activity_input.node,
        injected_results=activity_input.dep_results,
    )

    flow_result = await task

    result = flow_result.all_node_results[activity_input.node]

    return result.to_dict() if hasattr(result, "to_dict") else result


async def run_signal_activity(
    input_data: dict[str, Any],
    event_client: DurableEventClient,
) -> None:
    signal_input = SignalActivityInput.from_mapping(input_data)

    await event_client.raise_event(
        instance_id=signal_input.target_instance_id,
        event_name=signal_input.event_name,
        data=signal_input.data,
    )


async def run_direct_flow_activity(input_data: dict[str, Any]) -> Any:
    flow_name = input_data["flow_name"]
    base_inputs = input_data.get("base_inputs") or {}

    if not await is_telemetry_enabled():
        return await _run_direct_core(flow_name, base_inputs)

    traceparent = base_inputs.get("_traceparent")
    parent_ctx = propagator.extract({"traceparent": traceparent}) if traceparent else None
    span_name = f"durable.activity:direct:{flow_name}"

    with get_tracer(__name__).start_as_current_span(span_name, context=parent_ctx, kind=SpanKind.INTERNAL) as span:
        span.set_attribute("durable.kind", "direct")
        span.set_attribute("durable.flow_name", flow_name)
        try:
            return await _run_direct_core(flow_name, base_inputs)
        except Exception as exc:
            span.record_exception(exc)
            span.set_attribute("durable.error", str(exc))
            raise


async def _run_direct_core(flow_name: str, base_inputs: dict) -> dict:
    task = run_flow(flow_name, inputs=base_inputs)
    flow_result = await task

    return {
        k: (v.to_dict() if hasattr(v, "to_dict") else v)
        for k, v in flow_result.all_node_results.items()
    }


def get_jitter_factor_activity(max_jitter: float) -> float:
    import random

    try:
        m = float(max_jitter)
    except Exception:
        m = 0.0

    if m <= 0:
        return 0.0

    return random.random() * m


# ---------------------------------------------------------
# Internal steps
# ---------------------------------------------------------

def _read_orchestration_input(
    context: df.DurableOrchestrationContext,
) -> NodeOrchestrationInput:
    return NodeOrchestrationInput.from_mapping(
        context.get_input() or {}
    )


def _wait_for_dependency_results(
    *,
    context: df.DurableOrchestrationContext,
    upstream_nodes: list[str],
) -> DurableGenerator[dict[str, Any]]:
    ordered_upstream_nodes = sorted(upstream_nodes)

    if not ordered_upstream_nodes:
        return {}

    wait_tasks: list[DurableTask] = [
        context.wait_for_external_event(dependency_event_name(node))
        for node in ordered_upstream_nodes
    ]

    results = yield context.task_all(wait_tasks)

    return dict(zip(ordered_upstream_nodes, results))


def _run_node_activity(
    *,
    context: df.DurableOrchestrationContext,
    activity_name: str,
    retry_options: df.RetryOptions,
    retry_policy: DurableRetryPolicy | None,
    orchestration_input: NodeOrchestrationInput,
    dependency_results: dict[str, Any],
) -> DurableGenerator[Any]:
    activity_input = NodeActivityInput(
        node=orchestration_input.node,
        flow_name=orchestration_input.flow_name,
        base_inputs=orchestration_input.base_inputs,
        dep_results=dependency_results,
    )

    if retry_policy is not None:
        return (yield from _run_with_retry_policy(
            context=context,
            activity_name=activity_name,
            activity_input=activity_input,
            retry_policy=retry_policy,
        ))

    result = yield context.call_activity_with_retry(
        activity_name,
        retry_options,
        input_=activity_input.to_dict(),
    )

    return result


def _run_with_retry_policy(
    *,
    context: df.DurableOrchestrationContext,
    activity_name: str,
    activity_input: NodeActivityInput,
    retry_policy: DurableRetryPolicy,
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
            result = yield context.call_activity(
                activity_name,
                activity_input.to_dict(),
            )
            return result
        except Exception:
            if attempt == retry_policy.attempts - 1:
                raise


def _signal_downstream_nodes(
    *,
    context: df.DurableOrchestrationContext,
    signal_activity_name: str,
    retry_options: df.RetryOptions,
    orchestration_input: NodeOrchestrationInput,
    node_result: Any,
) -> DurableGenerator[None]:
    signal_tasks: list[DurableTask] = [
        context.call_activity_with_retry(
            signal_activity_name,
            retry_options,
            input_=SignalActivityInput(
                target_instance_id=target_instance_id,
                event_name=dependency_event_name(orchestration_input.node),
                data=node_result,
            ).to_dict(),
        )
        for _, target_instance_id in sorted(
            orchestration_input.downstream_instance_ids.items()
        )
    ]

    if signal_tasks:
        yield context.task_all(signal_tasks)

    return None
