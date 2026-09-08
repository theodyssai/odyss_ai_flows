from __future__ import annotations

from typing import Any

import networkx as nx
import azure.durable_functions as df

from odyss_ai_flows_durable._contracts.constants import (
    FLOW_ORCHESTRATOR,
    JITTER_ACTIVITY,
    NODE_ACTIVITY,
    NODE_ORCHESTRATOR,
    SIGNAL_ACTIVITY,
)

from odyss_ai_flows_durable._contracts.cycle_detection import (
    assert_dag_acyclic,
)

from odyss_ai_flows_durable._contracts.dag import (
    build_dag,
)

from odyss_ai_flows_durable._contracts.naming import (
    build_child_instance_id,
)

from odyss_ai_flows_durable._contracts.payloads import (
    FlowOrchestrationInput,
    NodeOrchestrationInput,
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

from odyss_ai_flows_durable._runtime._single.handlers import (
    get_jitter_factor_activity,
    run_node_activity,
    run_node_orchestration,
    run_signal_activity,
)

from odyss_ai_flows_durable._runtime._single.http_event_client import (
    DurableHttpEventClient,
)

from odyss_ai_flows_durable._runtime.base import (
    DurableFlowExecutor,
)


# ---------------------------------------------------------
# Public executor
# ---------------------------------------------------------

class DurableFunctionsExecutor(DurableFlowExecutor):

    def __init__(
        self,
        client: df.DurableOrchestrationClient,
        *,
        orchestrator_name: str = FLOW_ORCHESTRATOR,
        retry_policy: DurableRetryPolicy | None = None,
    ) -> None:
        self._client = client
        self._orchestrator_name = orchestrator_name
        self._retry_policy = retry_policy

    # -----------------------------------------------------
    # DurableFlowExecutor
    # -----------------------------------------------------

    async def start(
        self,
        flow: Any,
        *,
        inputs: dict[str, Any] | None = None,
        instance_id: str | None = None,
    ) -> str:
        flow_name = str(flow)
        graph = build_dag(flow_name)
        assert_dag_acyclic(graph, flow_name)

        return await self._execute(
            flow_name,
            inputs or {},
            instance_id,
        )

    # -----------------------------------------------------
    # Registration
    # -----------------------------------------------------

    @classmethod
    def register(
        cls,
        bp: df.Blueprint,
        *,
        event_client: DurableEventClient | None = None,
        retry_options: df.RetryOptions | None = None,
    ) -> None:
        resolved_client: DurableEventClient = (
            event_client or DurableHttpEventClient()
        )

        @bp.orchestration_trigger(
            context_name="context",
            orchestration=FLOW_ORCHESTRATOR,
        )
        def flow_orchestrator(context):
            payload = FlowOrchestrationInput.from_mapping(
                _get_mapping_input(context)
            )

            orchestrator = _DagOrchestrator(
                context,
                node_orchestrator_name=NODE_ORCHESTRATOR,
                retry_options=retry_options,
                retry_policy=payload.retry_policy,
            )

            result = yield from orchestrator.run(
                flow_name=payload.flow_name,
                inputs=payload.inputs,
                instance_id=context.instance_id,
            )

            return result

        @bp.orchestration_trigger(
            context_name="context",
            orchestration=NODE_ORCHESTRATOR,
        )
        def node_orchestrator(context):
            result = yield from run_node_orchestration(
                context,
                activity_name=NODE_ACTIVITY,
                signal_activity_name=SIGNAL_ACTIVITY,
                retry_options=retry_options,
            )

            return result

        @bp.activity_trigger(
            input_name="input_data",
            activity=NODE_ACTIVITY,
        )
        async def node_activity(input_data):
            return await run_node_activity(
                _ensure_mapping(input_data)
            )

        @bp.activity_trigger(
            input_name="input_data",
            activity=SIGNAL_ACTIVITY,
        )
        async def signal_event(input_data):
            await run_signal_activity(
                _ensure_mapping(input_data),
                resolved_client,
            )

        @bp.activity_trigger(
            input_name="max_jitter",
            activity=JITTER_ACTIVITY,
        )
        def jitter_activity(max_jitter):
            return get_jitter_factor_activity(max_jitter)

    # -----------------------------------------------------
    # Internal
    # -----------------------------------------------------

    async def _execute(
        self,
        flow_name: str,
        inputs: dict[str, Any],
        instance_id: str | None,
    ) -> str:
        payload = FlowOrchestrationInput(
            flow_name=flow_name,
            inputs=inputs,
            retry_policy=self._retry_policy.to_dict() if self._retry_policy else None,
        )

        return await self._client.start_new(
            orchestration_function_name=self._orchestrator_name,
            client_input=payload.to_dict(),
            instance_id=instance_id,
        )


# ---------------------------------------------------------
# Internal DAG orchestrator
# ---------------------------------------------------------

class _DagOrchestrator:

    def __init__(
        self,
        context: df.DurableOrchestrationContext,
        *,
        node_orchestrator_name: str = NODE_ORCHESTRATOR,
        retry_options: df.RetryOptions | None = None,
        retry_policy: dict[str, Any] | None = None,
    ) -> None:
        self._context = context
        self._node_orchestrator_name = node_orchestrator_name
        self._retry_options = (
            retry_options or df.RetryOptions(10, 1)
        )
        self._retry_policy = retry_policy

    def run(
        self,
        flow_name: str,
        *,
        inputs: dict[str, Any] | None = None,
        instance_id: str | None = None,
    ) -> DurableGenerator[dict[str, Any]]:
        graph = build_dag(flow_name)

        ordered_nodes = sorted(graph.nodes())
        downstream_by_node = {
            n: set(graph.predecessors(n)) for n in graph.nodes()
        }

        instance_id_by_node = _build_instance_ids(
            nodes=ordered_nodes,
            parent_instance_id=instance_id,
        )

        scheduled_nodes: dict[str, DurableTask] = {
            node: self._schedule_node_orchestrator(
                node=node,
                flow_name=flow_name,
                graph=graph,
                base_inputs=inputs or {},
                downstream_by_node=downstream_by_node,
                instance_id_by_node=instance_id_by_node,
            )
            for node in ordered_nodes
        }

        if not scheduled_nodes:
            return {}

        node_results = yield self._context.task_all(
            list(scheduled_nodes.values())
        )

        return dict(zip(scheduled_nodes.keys(), node_results))

    def _schedule_node_orchestrator(
        self,
        *,
        node: str,
        flow_name: str,
        graph: nx.DiGraph,
        base_inputs: dict[str, Any],
        downstream_by_node: dict[str, set[str]],
        instance_id_by_node: dict[str, str],
    ) -> DurableTask:
        orchestration_input = _build_node_orchestration_input(
            node=node,
            flow_name=flow_name,
            graph=graph,
            base_inputs=base_inputs,
            downstream_by_node=downstream_by_node,
            instance_id_by_node=instance_id_by_node,
            retry_policy=self._retry_policy,
        )

        return self._context.call_sub_orchestrator_with_retry(
            self._node_orchestrator_name,
            self._retry_options,
            input_=orchestration_input.to_dict(),
            instance_id=instance_id_by_node[node],
        )


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def _build_instance_ids(
    *,
    nodes: list[str],
    parent_instance_id: str | None,
) -> dict[str, str]:
    return {
        node: build_child_instance_id(
            parent_instance_id=parent_instance_id,
            node=node,
        )
        for node in nodes
    }


def _build_node_orchestration_input(
    *,
    node: str,
    flow_name: str,
    graph: nx.DiGraph,
    base_inputs: dict[str, Any],
    downstream_by_node: dict[str, set[str]],
    instance_id_by_node: dict[str, str],
    retry_policy: dict[str, Any] | None = None,
) -> NodeOrchestrationInput:
    downstream_instance_ids = {
        downstream_node: instance_id_by_node[downstream_node]
        for downstream_node in sorted(downstream_by_node.get(node, set()))
    }

    return NodeOrchestrationInput(
        node=node,
        flow_name=flow_name,
        base_inputs=base_inputs,
        upstream=sorted(graph.successors(node)),
        downstream_instance_ids=downstream_instance_ids,
        retry_policy=retry_policy,
    )


def _get_mapping_input(context: Any) -> dict[str, Any]:
    return _ensure_mapping(context.get_input())


def _ensure_mapping(value: object) -> dict[str, Any]:
    if value is None:
        return {}

    if not isinstance(value, dict):
        raise TypeError(
            "Durable input must be a dictionary, "
            f"got {type(value).__name__}."
        )

    return value
