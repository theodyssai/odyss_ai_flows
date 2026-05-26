from __future__ import annotations

from pathlib import Path

from odyss_ai_flows.core.runtime.runner import (
    run_flow,
)

from tests.tests_runtime.assertions import (
    assert_flow_success,
)


async def run_scenario():

    result = await run_flow(

        flow=Path(
            "area/flow"
        ),
    )

    assert_flow_success(result)

    # =============================================
    # Producer
    # =============================================

    producer = result["producer_node"]

    assert producer == {

        "initial_consumer_scalar":
            "consumer_initial",

        "initial_consumer_dict": {

            "a": 1,
        },
    }

    # =============================================
    # Consumer
    # =============================================

    consumer = result["consumer_node"]

    assert consumer == {

        "scalar":
            "consumer_overridden",

        "dict": {

            "a": 1,
            "b": 2,
        },

        "created":
            123,
    }

    # =============================================
    # Nested consumer
    # =============================================

    nested = result[
        "nested_consumer_node"
    ]

    assert nested == {

        "scalar":
            "nested_overridden",

        "dict": {

            "x": 10,
            "y": 20,
        },
    }

    # =============================================
    # Cache validation
    # =============================================

    cache = result[
        "cache_validation_node"
    ]

    assert cache == {

        "before": None,

        "after":
            "consumer_second_override",
    }