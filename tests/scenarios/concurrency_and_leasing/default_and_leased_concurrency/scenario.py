from __future__ import annotations

from odyss_ai_flows.core.runtime.runner import (
    run_flow,
)

from tests.tests_runtime.assertions import (
    assert_flow_success,
)

from tests.scenarios.concurrency_and_leasing.default_and_leased_concurrency import (
    shared,
)


async def run_scenario():

    # =============================================
    # Default strategy baseline
    # =============================================

    await shared.reset()

    default_result = await run_flow(
        "default_flow"
    )

    assert_flow_success(
        default_result
    )

    assert (
        shared.MAX_ACTIVE > 1
    )

    assert (
        shared.COMPLETED == 20
    )

    # =============================================
    # Leased concurrency
    # =============================================

    await shared.reset()

    leased_result = await run_flow(

        "leased_flow",

        max_concurrency=2,
    )

    assert_flow_success(
        leased_result
    )

    assert (
        shared.MAX_ACTIVE == 2
    )

    assert (
        shared.COMPLETED == 20
    )