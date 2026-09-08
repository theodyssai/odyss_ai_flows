from __future__ import annotations

import azure.durable_functions as df

from odyss_ai_flows_durable._contracts.constants import (
    SEQUENCE_ORCHESTRATOR,
)

from odyss_ai_flows_durable._runtime._group._sequence.orchestrator import (
    run_sequence_orchestration,
)

from odyss_ai_flows_durable._runtime._group.base import (
    GroupExecutor,
)


# ---------------------------------------------------------
# Public executor
# ---------------------------------------------------------

class DurableSequenceExecutor(GroupExecutor):

    @property
    def _orchestrator_name(self) -> str:
        return SEQUENCE_ORCHESTRATOR

    @classmethod
    def _register_orchestrator(cls, bp: df.Blueprint) -> None:
        @bp.orchestration_trigger(
            context_name="context",
            orchestration=SEQUENCE_ORCHESTRATOR,
        )
        def sequence_orchestrator(context: df.DurableOrchestrationContext):
            return (yield from run_sequence_orchestration(context))
