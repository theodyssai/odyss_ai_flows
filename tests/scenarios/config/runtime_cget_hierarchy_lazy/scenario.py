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

        variant_paths=[

            Path(
                "variants/v1/flow"
            ),
        ],
    )

    assert_flow_success(result)

    # =================================================
    # ROOT NODE
    # =================================================

    root_node = result["root_node"]

    assert root_node == {

        "scalar_replace": "root_node",

        "dict_merge": {

            "global": True,
            "ancestor": True,
            "flow": True,
            "root_node": True,
        },

        "list_replace": [
            "root_node"
        ],

        "nested": {

            "dict": {

                "global": 1,
                "ancestor": 2,
                "flow": 3,
                "root_node": 4,
            },

            "list": [
                "root_node"
            ],
        },
    }

    # =================================================
    # NESTED NODE
    # =================================================

    nested_node = result["nested_node"]

    assert nested_node == {

        "scalar_replace": "variant_nested_node",

        "dict_merge": {

            "global": True,
            "ancestor": True,
            "flow": True,
            "nested": True,
            "nested_node": True,
            "variant": True,
        },

        "list_replace": [
            "variant_nested_node"
        ],

        "nested": {

            "dict": {

                "global": 1,
                "ancestor": 2,
                "flow": 3,
                "nested": 4,
                "nested_node": 5,
                "variant": 6,
            },

            "list": [
                "variant_nested_node"
            ],
        },
    }