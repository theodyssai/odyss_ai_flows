# tests/tests_runtime/assertions.py

from __future__ import annotations

from typing import Any

from odyss_ai_flows.core.executor.raw_flow_result import (
    FlowStatus,
)

from odyss_ai_flows.core.runtime.flow_result import (
    FlowResult,
)


# ---------------------------------------------------------
# Core status assertions
# ---------------------------------------------------------

def assert_flow_success(
    result: FlowResult,
) -> None:

    if result.status != FlowStatus.SUCCESS:

        raise AssertionError(
            "Expected flow status SUCCESS\n\n"
            f"Actual: {result.status}"
        )


def assert_flow_failure(
    result: FlowResult,
) -> None:

    if result.status != FlowStatus.FAILURE:

        raise AssertionError(
            "Expected flow status FAILURE\n\n"
            f"Actual: {result.status}"
        )


def assert_flow_error(
    result: FlowResult,
) -> None:

    if result.status != FlowStatus.ERROR:

        raise AssertionError(
            "Expected flow status ERROR\n\n"
            f"Actual: {result.status}"
        )


def assert_flow_break(
    result: FlowResult,
) -> None:

    if result.status != FlowStatus.BREAK:

        raise AssertionError(
            "Expected flow status BREAK\n\n"
            f"Actual: {result.status}"
        )


# ---------------------------------------------------------
# Output assertions
# ---------------------------------------------------------

def assert_output_equals(
    result: FlowResult,
    key: str,
    expected: Any,
) -> None:

    actual = result.outputs.get(key)

    if actual != expected:

        raise AssertionError(
            f"Output mismatch for '{key}'\n\n"
            f"Expected:\n"
            f"{expected!r}\n\n"
            f"Actual:\n"
            f"{actual!r}"
        )


def assert_outputs_match(
    result: FlowResult,
    expected: dict[str, Any],
) -> None:

    actual = result.outputs

    if actual != expected:

        raise AssertionError(
            "Outputs mismatch\n\n"
            f"Expected:\n"
            f"{expected!r}\n\n"
            f"Actual:\n"
            f"{actual!r}"
        )


# ---------------------------------------------------------
# Error assertions
# ---------------------------------------------------------

def assert_error_contains(
    result: FlowResult,
    text: str,
) -> None:

    err = result.error

    if err is None:

        raise AssertionError(
            "Expected flow to contain error\n\n"
            "Actual: no error present"
        )

    err_text = str(err)

    if text not in err_text:

        raise AssertionError(
            "Expected error to contain text\n\n"
            f"Missing text:\n"
            f"{text}\n\n"
            f"Actual error:\n"
            f"{err_text}"
        )


# ---------------------------------------------------------
# Node assertions
# ---------------------------------------------------------

def assert_node_executed(
    result: FlowResult,
    node_name: str,
) -> None:

    if node_name not in result.all_node_results:

        raise AssertionError(
            f"Expected node '{node_name}' "
            f"to execute\n\n"
            f"Executed nodes:\n"
            f"{sorted(result.all_node_results.keys())}"
        )