from __future__ import annotations

from odyss_ai_flows.core.runtime.runner import (
    run_flow,
)

from odyss_ai_flows.core.executor.raw_flow_result import (
    FlowStatus,
)

from odyss_ai_flows.core.executor.exceptions import (
    NodeExecutionError,
    FrameworkError,
    FlowBreak,
)

from odyss_ai_flows.core.utils.logger import (
    logger,
)


async def run_scenario():

    logger.info(
        "=== FAILURE & BREAK SCENARIO START ==="
    )

    # =================================================
    # Immediate node failure
    # =================================================

    failure = await run_flow(
        "failure_flow",
        raise_on_fail=False,
    )

    logger.info(
        "[failure] status=%r error=%r "
        "suppressed=%r results=%r",
        failure.status,
        failure.error,
        failure.suppressed_error,
        failure.all_node_results,
    )

    assert (
        failure.status
        is FlowStatus.FAILURE
    )

    assert isinstance(
        failure.error,
        NodeExecutionError,
    )

    assert (
        "setup_node"
        in failure.all_node_results
    )

    # =================================================
    # raise_on_fail=True
    # =================================================

    try:

        await run_flow(
            "failure_flow",
            raise_on_fail=True,
        )

        raise AssertionError(
            "Expected failure reraising"
        )

    except NodeExecutionError:
        pass

    # =================================================
    # Framework error
    # =================================================

    try:

        await run_flow(
            "framework_error_flow",
            raise_on_fail=False,
        )

        raise AssertionError(
            "Expected FrameworkError"
        )

    except FrameworkError as e:

        logger.info(
            "[framework] caught=%r",
            e,
        )

        assert (
            "intentional framework error"
            in str(e)
                )

    # =================================================
    # Flow break
    # =================================================

    breaker = await run_flow(
        "break_flow",
        raise_on_fail=False,
    )

    logger.info(
        "[break] status=%r error=%r "
        "suppressed=%r results=%r",
        breaker.status,
        breaker.error,
        breaker.suppressed_error,
        breaker.all_node_results,
    )

    assert (
        breaker.status
        is FlowStatus.BREAK
    )

    assert isinstance(
        breaker.error,
        FlowBreak,
    )

    assert (
        "setup_node"
        in breaker.all_node_results
    )

    # =================================================
    # BREAK must not raise
    # =================================================

    breaker2 = await run_flow(
        "break_flow",
        raise_on_fail=True,
    )

    assert (
        breaker2.status
        is FlowStatus.BREAK
    )

    # =================================================
    # Timed overlapping failure
    # =================================================

    timed = await run_flow(
        "timed_failure_flow",
        raise_on_fail=False,
    )

    logger.info(
        "[timed] status=%r error=%r "
        "suppressed=%r results=%r",
        timed.status,
        timed.error,
        timed.suppressed_error,
        timed.all_node_results,
    )

    assert (
        timed.status
        is FlowStatus.FAILURE
    )

    assert isinstance(
        timed.error,
        NodeExecutionError,
    )

    assert (
        "setup_node"
        in timed.all_node_results
    )

    logger.info(
        "=== FAILURE & BREAK SCENARIO END ==="
    )