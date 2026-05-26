from __future__ import annotations

from odyss_ai_flows.core.runtime.runner import (
    run_flow,
)

from tests.tests_runtime.assertions import (
    assert_flow_success,
)

from tests.scenarios.concurrency_and_leasing.dependency_lease_release import (
    shared,
)


async def run_scenario():

    await shared.reset()

    result = await run_flow(

        "flow",

        max_concurrency=2,
    )

    assert_flow_success(
        result
    )

    # =========================================
    # Producer must have executed
    # =========================================

    assert (
        "producer:start"
        in
        shared.EVENTS
    )

    assert (
        "producer:end"
        in
        shared.EVENTS
    )

    # =========================================
    # All consumers resumed
    # after producer completion
    # =========================================

    resumed = [

        e for e
        in shared.EVENTS

        if e.endswith(":resumed")
    ]

    assert len(
        resumed
    ) == 3

    # =========================================
    # Ensure all nodes completed
    # =========================================

    assert set(
        result.outputs.keys()
    ) == {

        "producer",
        "consumer_1",
        "consumer_2",
        "consumer_3",
    }