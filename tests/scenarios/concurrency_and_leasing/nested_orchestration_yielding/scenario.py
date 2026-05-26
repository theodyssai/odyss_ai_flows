from __future__ import annotations

import asyncio

from odyss_ai_flows.core.runtime.runner import (
    run_flow,
)

from tests.tests_runtime.assertions import (
    assert_flow_success,
)

from tests.scenarios.concurrency_and_leasing.nested_orchestration_yielding import (
    shared,
)


async def run_scenario():

    await shared.reset()

    shared.install()

    try:

        results = await asyncio.gather(

            run_flow(
                "top_flow"
            ),

            run_flow(
                "top_flow"
            ),

            run_flow(
                "top_flow"
            ),
        )

        for result in results:

            assert_flow_success(
                result
            )

        # =====================================
        # Hard lease limit respected
        # =====================================

        assert (
            shared.MAX_ACTIVE <= 2
        )

        # =====================================
        # Enough orchestration activity
        # actually happened
        # =====================================

        acquire_count = sum(

            1

            for e
            in shared.EVENTS

            if e == "acquire"
        )

        release_count = sum(

            1

            for e
            in shared.EVENTS

            if e == "release"
        )

        reacquire_count = sum(

            1

            for e
            in shared.EVENTS

            if e == "reacquire"
        )

        assert acquire_count >= 10

        assert release_count >= 5

        assert reacquire_count >= 5

        # =====================================
        # Final state sanity
        # =====================================

        assert (
            shared.CURRENT_ACTIVE == 0
        )

    finally:

        shared.uninstall()