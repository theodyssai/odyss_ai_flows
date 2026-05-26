from __future__ import annotations

from odyss_ai_flows.core.runtime.runner import (
    run_flow,
)

from tests.tests_runtime.assertions import (
    assert_flow_success,
)

from tests.scenarios.concurrency_and_leasing.custom_strategy_injection.custom_strategy import (
    RecordingStrategy,
)

from tests.scenarios.concurrency_and_leasing.custom_strategy_injection import (
    shared,
)


async def run_scenario():

    await shared.reset()

    result = await run_flow(

        "flow",

        strategy=RecordingStrategy(),
    )

    assert_flow_success(
        result
    )

    # =========================================
    # run_node interception
    # =========================================

    assert any(

        e.startswith(
            "run:"
        )

        for e in shared.EVENTS
    )

    # =========================================
    # await interception
    # =========================================

    assert (
        "await:start"
        in
        shared.EVENTS
    )

    assert (
        "await:end"
        in
        shared.EVENTS
    )

    # =========================================
    # actual flow correctness
    # =========================================

    assert result[
        "consumer"
    ] == "producer_value"