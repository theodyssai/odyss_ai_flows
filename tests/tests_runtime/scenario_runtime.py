from __future__ import annotations

import inspect

from tests.tests_runtime.scenario_protocol import (
    ScenarioRuntimeDefinition,
)


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

async def _execute_run_flow(
    definition: ScenarioRuntimeDefinition,
):

    from odyss_ai_flows.core.runtime.runner import (
        run_flow,
    )

    return await run_flow(
        flow=definition.flow,
        inputs=definition.inputs,
        variant_paths=definition.variant_paths,
        run_name=definition.run_name,
        raise_on_fail=definition.raise_on_fail,
    )


async def _run_assertions(
    result,
    assertions,
) -> None:

    for assertion in assertions:

        outcome = assertion(result)

        if inspect.isawaitable(outcome):
            await outcome


# ---------------------------------------------------------
# Public API
# ---------------------------------------------------------

async def execute_scenario(
    runtime: ScenarioRuntimeDefinition,
):

    result = await _execute_run_flow(
        runtime
    )

    await _run_assertions(
        result,
        runtime.assertions,
    )

    return result