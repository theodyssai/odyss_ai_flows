from __future__ import annotations

from odyss_ai_flows.core.runtime.runner import (
    run_flow,
)

from tests.tests_runtime.assertions import (
    assert_flow_success,
)

from tests.scenarios.concurrency_and_leasing.manual_nested_leasing.shared import (
    install,
    uninstall,
)


async def run_scenario():

    install()

    try:

        result = await run_flow(
            "top_flow"
        )

        assert_flow_success(
            result
        )

    finally:

        uninstall()