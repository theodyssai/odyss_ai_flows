from __future__ import annotations

from odyss_ai_flows.core.runtime.runner import (
    run_flow,
)

from odyss_ai_flows.core.handlers.middleware.middleware import (
    register_middleware,
)

from tests.tests_runtime.assertions import (
    assert_flow_success,
)

from tests.scenarios.handlers_middleware_semantics.shared import (
    TRACE,
)


# =================================================
# Middleware A
# =================================================

def middleware_a(call, handler):

    async def wrapped(**kwargs):

        TRACE.append(
            f"{handler.node.name}:a_before"
        )

        result = await call(
            **kwargs
        )

        TRACE.append(
            f"{handler.node.name}:a_after"
        )

        return result

    return wrapped


# =================================================
# Middleware B
# =================================================

def middleware_b(call, handler):

    async def wrapped(**kwargs):

        TRACE.append(
            f"{handler.node.name}:b_before"
        )

        result = await call(
            **kwargs
        )

        TRACE.append(
            f"{handler.node.name}:b_after"
        )

        return result

    return wrapped


# =================================================
# Short-circuit middleware
# =================================================

def short_circuit_middleware(call, handler):

    async def wrapped(**kwargs):

        TRACE.append(
            f"{handler.node.name}:short_circuit"
        )

        return {

            "blocked":
                True
        }

    return wrapped


# =================================================
# Failure middleware
# =================================================

def failure_middleware(call, handler):

    async def wrapped(**kwargs):

        TRACE.append(
            f"{handler.node.name}:failure"
        )

        raise RuntimeError(
            "middleware failure"
        )

    return wrapped


# =================================================
# Register middleware
# =================================================

register_middleware(
    "middleware_a",
    middleware_a,
)

register_middleware(
    "middleware_b",
    middleware_b,
)

register_middleware(
    "short_circuit",
    short_circuit_middleware,
)

register_middleware(
    "failure",
    failure_middleware,
)


async def run_scenario():

    # =============================================
    # Ordering semantics (same node only)
    # =============================================

    TRACE.clear()

    ordering = await run_flow(
        "ordering_flow"
    )

    assert_flow_success(
        ordering
    )

    assert TRACE == [

        "ordered_node:a_before",
        "ordered_node:b_before",
        "ordered_node:node",
        "ordered_node:b_after",
        "ordered_node:a_after",
    ]

    # =============================================
    # Middleware isolation semantics
    # =============================================

    TRACE.clear()

    isolated = await run_flow(
        "isolated_flow"
    )

    assert_flow_success(
        isolated
    )

    # ---------------------------------------------
    # Presence only
    # ---------------------------------------------

    expected = {

        "node_a:a_before",
        "node_a:node",
        "node_a:a_after",

        "node_b:b_before",
        "node_b:node",
        "node_b:b_after",
    }

    assert set(
        TRACE
    ) == expected

    # ---------------------------------------------
    # Intra-node ordering only
    # ---------------------------------------------

    a_before = TRACE.index(
        "node_a:a_before"
    )

    a_node = TRACE.index(
        "node_a:node"
    )

    a_after = TRACE.index(
        "node_a:a_after"
    )

    assert (
        a_before
        <
        a_node
        <
        a_after
    )

    b_before = TRACE.index(
        "node_b:b_before"
    )

    b_node = TRACE.index(
        "node_b:node"
    )

    b_after = TRACE.index(
        "node_b:b_after"
    )

    assert (
        b_before
        <
        b_node
        <
        b_after
    )

    # =============================================
    # Short-circuit semantics
    # =============================================

    TRACE.clear()

    shorted = await run_flow(
        "short_circuit_flow"
    )

    assert_flow_success(
        shorted
    )

    assert TRACE == [

        "shorted_node:short_circuit"
    ]

    assert shorted[
        "shorted_node"
    ] == {

        "blocked":
            True
    }

    # =============================================
    # Middleware exception propagation
    # =============================================

    TRACE.clear()

    failed = await run_flow(

        "failure_flow",

        raise_on_fail=False,
    )

    assert (
        failed.status.value
        ==
        "failure"
    )

    assert (
        "failing_node:failure"
        in TRACE
    )

    assert (
        "middleware failure"
        in str(
            failed.error
        )
    )