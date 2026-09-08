from __future__ import annotations

from tests.tests_runtime.assertions import (
    assert_flow_success,
)

from odyss_ai_flows.core.runtime.runner import (
    run_flow,
)

from odyss_ai_flows.core.runtime.flow_result import (
    FlowResult,
)

from tests.scenarios.runtime.runtime_outputs_and_serialization.helpers.objects import (
    ComplexObject,
)


async def run_scenario():

    result = await run_flow(
        "area/flow",
    )

    assert_flow_success(
        result
    )

    # =====================================================
    # Export surface
    # =====================================================

    outputs = result.outputs

    assert set(outputs.keys()) == {

        "public_summary",
        "renamed_nested",
        "renamed_object",
    }

    # =====================================================
    # Collection protocol respects projection
    # =====================================================

    expected_keys = {
        "public_summary",
        "renamed_nested",
        "renamed_object",
    }

    assert set(result.keys()) == expected_keys

    assert set(result) == expected_keys

    assert len(result) == 3

    assert "public_summary" in result

    # Filtered node absent from collection surface
    assert "hidden_internal" not in result

    # Remapped-away raw name absent from collection surface
    assert "producer_a" not in result

    # Shallow dict conversion mirrors outputs
    assert dict(result) == result.outputs

    assert dict(result.items()) == result.outputs

    assert set(dict(result.items()).keys()) == expected_keys

    # values() reflects projected values
    assert (
        dict(zip(result.keys(), result.values()))
        == result.outputs
    )

    # =====================================================
    # Mapping semantics
    # =====================================================

    assert result[
        "public_summary"
    ] == "summary"

    obj = result[
        "renamed_object"
    ]

    assert isinstance(
        obj,
        ComplexObject,
    )

    assert obj.value == 123

    # =====================================================
    # Old name blocked by mapping
    # =====================================================

    try:

        result[
            "producer_a"
        ]

        raise AssertionError(
            "old unmapped name unexpectedly accessible"
        )

    except KeyError:
        pass

    # =====================================================
    # Filtering semantics
    # =====================================================

    try:

        result[
            "hidden_internal"
        ]

        raise AssertionError(
            "filtered node unexpectedly accessible"
        )

    except KeyError:
        pass

    # =====================================================
    # Nested FlowResult preserved
    # =====================================================

    nested = result[
        "renamed_nested"
    ]

    assert isinstance(
        nested,
        FlowResult,
    )

    # =====================================================
    # Nested projection semantics
    # =====================================================

    assert nested[
        "visible_value"
    ] == "nested_visible"

    assert set(
        nested.outputs.keys()
    ) == {

        "visible_value",
    }

    # =====================================================
    # Nested filtering semantics
    # =====================================================

    try:

        nested[
            "hidden_nested"
        ]

        raise AssertionError(
            "hidden nested node unexpectedly accessible"
        )

    except KeyError:
        pass

    # =====================================================
    # Raw graph still preserved
    # =====================================================

    internal = (
        result.all_node_results
    )

    assert (
        "producer_a"
        in internal
    )

    assert (
        "hidden_internal"
        in internal
    )

    runtime_obj = internal[
        "producer_a"
    ]

    assert isinstance(
        runtime_obj,
        ComplexObject,
    )

    assert runtime_obj.value == 123

    assert (
        internal[
            "hidden_internal"
        ]
        == "hidden"
    )

    # =====================================================
    # Nested raw graph preserved
    # =====================================================

    nested_internal = internal[
        "nested_runner"
    ]

    assert isinstance(
        nested_internal,
        FlowResult,
    )

    assert (
        "hidden_nested"
        in nested_internal.all_node_results
    )

    assert (
        nested_internal
        .all_node_results[
            "hidden_nested"
        ]
        == "nested_hidden"
    )

    # =====================================================
    # outputs property consistency
    # =====================================================

    assert (
        result.outputs[
            "public_summary"
        ]
        ==
        result[
            "public_summary"
        ]
    )

    # =====================================================
    # Serialization degradation semantics
    # =====================================================

    json_text = (
        result.to_json()
    )

    assert isinstance(
        json_text,
        str,
    )

    # -----------------------------------------------------
    # Complex runtime object degraded safely
    # -----------------------------------------------------

    assert (
        "ComplexObject(123)"
        in json_text
    )

    # -----------------------------------------------------
    # Exported names serialized
    # -----------------------------------------------------

    assert (
        "public_summary"
        in json_text
    )

    assert (
        "renamed_nested"
        in json_text
    )

    assert (
        "renamed_object"
        in json_text
    )

    # -----------------------------------------------------
    # Hidden internal names absent
    # -----------------------------------------------------

    assert (
        "hidden_internal"
        not in json_text
    )

    # =====================================================
    # Nested serialization coherence
    # =====================================================

    nested_json = (
        nested.to_json()
    )

    assert (
        "visible_value"
        in nested_json
    )

    assert (
        "hidden_nested"
        not in nested_json
    )