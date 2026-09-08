from __future__ import annotations

from odyss_ai_flows.core.runtime.runner import (
    run_flow,
)

from odyss_ai_flows.core.executor.raw_flow_result import (
    FlowStatus,
)

from odyss_ai_flows.core.executor.exceptions import (
    CycleDetectedError,
)

from odyss_ai_flows.core.utils.logger import (
    logger,
)


def _assert_closed_cycle(path: list[str], expected_nodes: set[str]) -> None:

    assert path[0] == path[-1]

    assert set(path) == expected_nodes


async def run_scenario():

    logger.info(
        "=== CYCLE DETECTION SCENARIO START ==="
    )

    # =================================================
    # Direct 2-node cycle (both eager)
    # =================================================

    try:

        await run_flow(
            "direct_cycle_flow",
            raise_on_fail=False,
        )

        raise AssertionError(
            "Expected CycleDetectedError"
        )

    except CycleDetectedError as e:

        logger.info(
            "[direct] caught=%r",
            e,
        )

        _assert_closed_cycle(
            e.path,
            {"a", "b"},
        )

    # =================================================
    # Indirect 3-node cycle
    # =================================================

    try:

        await run_flow(
            "indirect_cycle_flow",
            raise_on_fail=False,
        )

        raise AssertionError(
            "Expected CycleDetectedError"
        )

    except CycleDetectedError as e:

        logger.info(
            "[indirect] caught=%r",
            e,
        )

        _assert_closed_cycle(
            e.path,
            {"a", "b", "c"},
        )

    # =================================================
    # Cycle through a lazily-launched node
    # =================================================

    try:

        await run_flow(
            "lazy_cycle_flow",
            raise_on_fail=False,
        )

        raise AssertionError(
            "Expected CycleDetectedError"
        )

    except CycleDetectedError as e:

        logger.info(
            "[lazy] caught=%r",
            e,
        )

        _assert_closed_cycle(
            e.path,
            {"eager_node", "lazy_node"},
        )

    # =================================================
    # Diamond fan-in must NOT be flagged as a cycle
    # =================================================

    diamond = await run_flow(
        "diamond_flow",
        raise_on_fail=False,
    )

    logger.info(
        "[diamond] status=%r results=%r",
        diamond.status,
        diamond.all_node_results,
    )

    assert (
        diamond.status
        is FlowStatus.SUCCESS
    )

    assert (
        diamond["c"]
        == 5
    )

    logger.info(
        "=== CYCLE DETECTION SCENARIO END ==="
    )
