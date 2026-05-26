from __future__ import annotations

from pathlib import Path

from odyss_ai_flows.core.runtime.runner import (
    run_flow,
)

from tests.tests_runtime.assertions import (
    assert_flow_success,
)


async def run_scenario():

    #
    # Intentionally conflicting tree.
    #
    # Filesystem config should NOT win.
    #

    provided_tree = {

        "name": "",
        "path": ".",

        "config": {

            "global_value":
                "provided_global",

            "shared": {
                "x": 1,
            },
        },

        "children": {

            "area": {

                "name": "area",
                "path": "area",

                "config": {},

                "children": {

                    "flow": {

                        "name": "flow",
                        "path": "area/flow",

                        "config": {},

                        "children": {

                            "runtime_node": {

                                "name": "runtime_node",

                                "path":
                                    "area/flow/runtime_node",

                                "config": {

                                    "node_value":
                                        "provided_node",

                                    "shared": {
                                        "y": 2,
                                    },
                                },

                                "children": {},
                            }
                        },
                    }
                },
            }
        },
    }

    result = await run_flow(

        flow=Path(
            "area/flow"
        ),

        provided_tree=provided_tree,

        pre_resolve_config=True,
    )

    assert_flow_success(result)

    runtime = result[
        "runtime_node"
    ]

    assert runtime == {

        "global_value":
            "provided_global",

        "node_value":
            "provided_node",

        "shared": {

            "x": 1,
            "y": 2,
        },
    }