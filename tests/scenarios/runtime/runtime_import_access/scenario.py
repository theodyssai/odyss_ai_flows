from __future__ import annotations

from tests.tests_runtime.assertions import (
    assert_flow_success,
)

from odyss_ai_flows.core.runtime.runner import (
    run_flow,
)

from tests.scenarios.runtime.runtime_import_access.area.flow.node_a import (
    some_completely_irrelevant_function_name,
)

from tests.scenarios.runtime.runtime_import_access.area.flow.node_b import (
    another_irrelevant_function_name,
)

from tests.scenarios.runtime.runtime_import_access.area.flow.hidden_node import (
    hidden_function,
)


async def run_scenario():

    result = await run_flow(
        "area/flow"
    )

    assert_flow_success(
        result
    )

    # =========================================
    # Import-based output lookup
    # =========================================

    assert result[
        some_completely_irrelevant_function_name
    ] == "value_a"

    assert result[
        another_irrelevant_function_name
    ] == "value_b"

    # =========================================
    # Callable lookup bypasses mapping
    # but respects filtering
    # =========================================

    assert result[
        some_completely_irrelevant_function_name
    ] == "value_a"

    assert result[
        "renamed_a"
    ] == "value_a"

    # =========================================
    # Mapping affects string access
    # =========================================

    try:

        result[
            "node_a"
        ]

        raise AssertionError(
            "raw node name unexpectedly accessible"
        )

    except KeyError:
        pass

    assert result[
        "renamed_a"
    ] == "value_a"

    # =========================================
    # Callable lookup respects filtering
    # =========================================

    try:

        result[
            hidden_function
        ]

        raise AssertionError(
            "filtered callable unexpectedly accessible"
        )

    except KeyError:
        pass

    # =========================================
    # Raw graph still preserved
    # =========================================

    assert (
        result
        .all_node_results[
            "hidden_node"
        ]
        ==
        "hidden"
    )

    # =========================================
    # Import aliasing works
    # =========================================

    alias = (
        some_completely_irrelevant_function_name
    )

    assert result[
        alias
    ] == "value_a"

    # =========================================
    # nget via callable worked
    # indirectly through node_b
    # =========================================

    assert result[
        another_irrelevant_function_name
    ] == "value_b"

    # =========================================
    # outputs property consistent
    # =========================================

    assert set(
        result.outputs.keys()
    ) == {

        "renamed_a",
        "node_b",
    }