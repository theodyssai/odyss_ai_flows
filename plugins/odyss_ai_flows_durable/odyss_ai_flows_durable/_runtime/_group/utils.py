from __future__ import annotations

from copy import deepcopy
from typing import Any

from odyss_ai_flows_durable._contracts.constants import (
    DIRECT_FLOW_ACTIVITY,
    FLOW_ORCHESTRATOR,
)

from odyss_ai_flows_durable._contracts.flows import (
    DispatchMode,
    DurableFlowStep,
    DurableSubflowGroup,
    DurableSubflowOutput,
)

from odyss_ai_flows_durable._contracts.payloads import (
    FlowOrchestrationInput,
)

from odyss_ai_flows_durable._contracts.types import (
    DurableTask,
)


# ---------------------------------------------------------
# Step scheduling
# ---------------------------------------------------------

def schedule_step(
    context: Any,
    step: DurableFlowStep,
    base_inputs: dict[str, Any],
) -> DurableTask:
    filtered_base = (
        {k: base_inputs[k] for k in step.input_keys if k in base_inputs}
        if step.input_keys is not None
        else base_inputs
    )

    step_inputs = merge(filtered_base, step.inputs)

    if step.mode == DispatchMode.DIRECT:
        return context.call_activity(
            DIRECT_FLOW_ACTIVITY,
            {
                "flow_name": step.flow_name,
                "base_inputs": step_inputs,
            },
        )

    return context.call_sub_orchestrator(
        FLOW_ORCHESTRATOR,
        FlowOrchestrationInput(
            flow_name=step.flow_name,
            inputs=step_inputs,
        ).to_dict(),
    )


# ---------------------------------------------------------
# Subflow extraction
# ---------------------------------------------------------

DEFAULT_SUBFLOW_GROUP_KEY = "__default__"


def extract_subflow_groups(result: Any) -> list[DurableSubflowGroup]:
    if not isinstance(result, dict):
        return []

    outputs = [
        DurableSubflowOutput.from_dict(value)
        for value in result.values()
        if DurableSubflowOutput.is_serialized(value)
    ]

    if not outputs:
        return []

    if not any(output.groups for output in outputs):
        flat_steps = [step for output in outputs for step in output.subflows]

        if not flat_steps:
            return []

        return [DurableSubflowGroup(key=DEFAULT_SUBFLOW_GROUP_KEY, steps=flat_steps)]

    groups: list[DurableSubflowGroup] = []

    for output in outputs:
        for group in output.groups:
            groups.append(DurableSubflowGroup(
                key=group.key,
                steps=group.steps,
                config=group.config.resolved(output.default_group_config),
            ))

        if output.subflows:
            groups.append(DurableSubflowGroup(key=DEFAULT_SUBFLOW_GROUP_KEY, steps=output.subflows))

    return groups


# ---------------------------------------------------------
# Deep merge
# ---------------------------------------------------------

def merge(base: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)

    for key, value in update.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge(result[key], value)
        else:
            result[key] = deepcopy(value)

    return result
