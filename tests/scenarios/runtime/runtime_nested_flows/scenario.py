from __future__ import annotations

from tests.tests_runtime.assertions import (
    assert_flow_success,
)

from odyss_ai_flows.core.runtime.runner import (
    run_flow,
)

from tests.scenarios.runtime.runtime_nested_flows.helpers.shared_state import (
    reset_state,
)


async def run_scenario():

    reset_state()

    result = await run_flow(
        "area/flow",
        run_name="top_run",
    )

    assert_flow_success(
        result
    )

    # =========================================
    # Orchestrator nested runs
    # =========================================

    orchestrator = result[
        "orchestrator_node"
    ]

    runs = orchestrator[
        "nested_run_names"
    ]

    tops = orchestrator[
        "top_names"
    ]

    assert (
        len(runs)
        == 3
    )

    assert (
        "nested in: area\\flow\\orchestrator_node"
        in runs[0]
    )

    assert (
        "index: 0"
        in runs[0]
    )

    assert (
        "index: 1"
        in runs[1]
    )

    # =========================================
    # Explicit nested override
    # =========================================

    assert (
        runs[2]
        == "manual_nested_run"
    )

    # =========================================
    # Shared top-level name
    # =========================================

    assert tops == [

        "top_run",
        "top_run",
        "top_run",
    ]

    # =========================================
    # Sibling node counter independence
    # =========================================

    sibling = result[
        "sibling_node"
    ]

    sibling_name = sibling[
        "nested_run_name"
    ]

    assert (
        "nested in: area\\flow\\sibling_node"
        in sibling_name
    )

    assert (
        "index: 0"
        in sibling_name
    )

    # =========================================
    # Shared mutable state after sync
    # =========================================

    lazy = result[
        "lazy_summary_node"
    ]

    assert (
        lazy["execution_count"]
        == 4
    )

    # =========================================
    # Nested FlowResult propagation
    # =========================================

    propagated = result[
        "propagation_node"
    ]

    assert (
        propagated["nested_value"]
        == "nested_result"
    )