from __future__ import annotations

from abc import ABC, abstractmethod

from typing import Any

from odyss_ai_flows import run_flow as _core_run_flow


# ---------------------------------------------------------
# Executor base
# ---------------------------------------------------------

class DurableFlowExecutor(ABC):

    @abstractmethod
    async def start(
        self,
        flow: Any,
        *,
        inputs: dict[str, Any] | None = None,
        instance_id: str | None = None,
    ) -> str:
        ...


# ---------------------------------------------------------
# Entry point
# ---------------------------------------------------------

async def run_durable_flow(
    flow: Any,
    executor: DurableFlowExecutor | None = None,
    *,
    inputs: dict[str, Any] | None = None,
    instance_id: str | None = None,
    **core_kwargs: Any,
) -> Any:
    if executor is not None:
        return await executor.start(
            flow,
            inputs=inputs,
            instance_id=instance_id,
        )

    return await _core_run_flow(flow, inputs=inputs, **core_kwargs)
