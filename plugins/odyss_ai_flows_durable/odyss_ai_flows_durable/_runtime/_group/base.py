from __future__ import annotations

from abc import abstractmethod
from typing import Any

import azure.durable_functions as df

from odyss_ai_flows_durable._contracts.constants import (
    DIRECT_FLOW_ACTIVITY,
    SUBFLOWS_ORCHESTRATOR,
    VIRTUAL_SPAN_ACTIVITY,
)

from odyss_ai_flows_durable._contracts.flows import (
    DurableFlowPlan,
)

from odyss_ai_flows_durable._contracts.protocols import (
    DurableEventClient,
)

from odyss_ai_flows_durable._runtime._single.executor import (
    DurableFunctionsExecutor,
)

from odyss_ai_flows_durable._runtime._single.handlers import (
    run_direct_flow_activity,
)

from odyss_ai_flows_durable._telemetry import build_virtual_span

from odyss_ai_flows_durable._runtime._group._subflows.orchestrator import (
    run_subflows_orchestration,
)

from odyss_ai_flows_durable._contracts.retry import (
    DurableRetryPolicy,
)

from odyss_ai_flows_durable._runtime.base import (
    DurableFlowExecutor,
)


# ---------------------------------------------------------
# Group executor base
# ---------------------------------------------------------

class GroupExecutor(DurableFlowExecutor):

    def __init__(
        self,
        client: df.DurableOrchestrationClient,
        *,
        retry_policy: DurableRetryPolicy | None = None,
    ) -> None:
        self._client = client
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
        if not isinstance(flow, DurableFlowPlan):
            raise TypeError(
                f"{type(self).__name__} requires a DurableFlowPlan, "
                f"got {type(flow).__name__}."
            )

        payload = {
            **flow.to_dict(),
            "base_inputs": inputs or {},
            "retry_policy": self._retry_policy.to_dict() if self._retry_policy else None,
        }

        return await self._client.start_new(
            orchestration_function_name=self._orchestrator_name,
            client_input=payload,
            instance_id=instance_id,
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
        cls._register_shared(bp, event_client=event_client, retry_options=retry_options)
        cls._register_orchestrator(bp)

    @classmethod
    def _register_shared(
        cls,
        bp: df.Blueprint,
        *,
        event_client: DurableEventClient | None = None,
        retry_options: df.RetryOptions | None = None,
    ) -> None:
        DurableFunctionsExecutor.register(
            bp,
            event_client=event_client,
            retry_options=retry_options,
        )

        @bp.activity_trigger(
            input_name="input_data",
            activity=DIRECT_FLOW_ACTIVITY,
        )
        async def direct_flow_activity(input_data: dict) -> Any:
            return await run_direct_flow_activity(
                input_data if isinstance(input_data, dict) else {}
            )

        @bp.activity_trigger(
            input_name="input_data",
            activity=VIRTUAL_SPAN_ACTIVITY,
        )
        async def build_virtual_span_activity(input_data: dict) -> dict:
            return await build_virtual_span(
                input_data if isinstance(input_data, dict) else {}
            )

        @bp.orchestration_trigger(
            context_name="context",
            orchestration=SUBFLOWS_ORCHESTRATOR,
        )
        def subflows_orchestrator(context: df.DurableOrchestrationContext):
            return (yield from run_subflows_orchestration(context))

    # -----------------------------------------------------
    # Subclass interface
    # -----------------------------------------------------

    @property
    @abstractmethod
    def _orchestrator_name(self) -> str:
        ...

    @classmethod
    @abstractmethod
    def _register_orchestrator(cls, bp: df.Blueprint) -> None:
        ...


# ---------------------------------------------------------
# Combined registration (sequence + parallel on one blueprint)
# ---------------------------------------------------------

def register_durable_support(
    bp: df.Blueprint,
    *,
    event_client: DurableEventClient | None = None,
    retry_options: df.RetryOptions | None = None,
) -> None:
    from odyss_ai_flows_durable._runtime._group._sequence.executor import (
        DurableSequenceExecutor,
    )
    from odyss_ai_flows_durable._runtime._group._parallel.executor import (
        DurableParallelExecutor,
    )

    GroupExecutor._register_shared(
        bp,
        event_client=event_client,
        retry_options=retry_options,
    )

    DurableSequenceExecutor._register_orchestrator(bp)
    DurableParallelExecutor._register_orchestrator(bp)
