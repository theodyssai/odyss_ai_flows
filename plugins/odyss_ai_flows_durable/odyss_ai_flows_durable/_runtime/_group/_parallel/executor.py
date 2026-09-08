from __future__ import annotations

import azure.durable_functions as df

from odyss_ai_flows_durable._contracts.constants import (
    PARALLEL_ORCHESTRATOR,
)

from odyss_ai_flows_durable._runtime._group._parallel.orchestrator import (
    run_parallel_orchestration,
)

from odyss_ai_flows_durable._runtime._group.base import (
    GroupExecutor,
)


# ---------------------------------------------------------
# Public executor
# ---------------------------------------------------------

class DurableParallelExecutor(GroupExecutor):

    @property
    def _orchestrator_name(self) -> str:
        return PARALLEL_ORCHESTRATOR

    @classmethod
    def _register_orchestrator(cls, bp: df.Blueprint) -> None:
        @bp.orchestration_trigger(
            context_name="context",
            orchestration=PARALLEL_ORCHESTRATOR,
        )
        def parallel_orchestrator(context: df.DurableOrchestrationContext):
            return (yield from run_parallel_orchestration(context))
