from __future__ import annotations

from tests.tests_runtime.assertions import (
    assert_flow_success,
)

from odyss_ai_flows.core.runtime.runner import (
    run_flow,
)

from tests.scenarios.runtime.runtime_nget_reuse.helpers.shared_state import (
    reset_state,
)


async def run_scenario():

    reset_state()

    result = await run_flow(
        "area/flow",
    )

    assert_flow_success(
        result
    )

    # =========================================
    # Shared dependency
    # =========================================

    shared = result[
        "shared_dependency"
    ]

    assert (
        shared["execution_count"]
        == 1
    )

    # =========================================
    # Repeated reuse
    # =========================================

    repeated = result[
        "repeated_reader"
    ]

    assert (
        repeated["same_identity"]
        is True
    )

    # =========================================
    # Concurrent reuse
    # =========================================

    concurrent = result[
        "concurrent_reader"
    ]

    assert (
        concurrent["same_identity"]
        is True
    )

    # =========================================
    # Delayed reuse
    # =========================================

    delayed = result[
        "delayed_reader"
    ]

    assert (
        delayed["same_identity"]
        is True
    )

    # =========================================
    # Dynamic branching
    # =========================================

    dynamic = result[
        "dynamic_reader"
    ]

    assert (
        dynamic["selected"]
        == "dynamic_dependency_a"
    )

    assert (
        dynamic["a_executed"]
        == 1
    )

    assert (
        dynamic["b_executed"]
        == 0
    )

    # =========================================
    # Lazy activation
    # =========================================

    lazy = result[
        "lazy_activation_reader"
    ]

    assert (
        lazy["before"]
        == 0
    )

    assert (
        lazy["after"]
        == 1
    )