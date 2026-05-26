from __future__ import annotations
import textwrap

from pathlib import Path

from odyss_ai_flows.core.runtime.prepared_flow import (
    PreparedFlow,
)

from odyss_ai_flows.core.runtime.runner import (
    run_flow,
)

from tests.tests_runtime.assertions import (
    assert_flow_success,
)

from tests.scenarios.runtime.runtime_prepared_flows.shared.external_node import (
    imported_external_function,
)


# =================================================
# Pure runtime callable
# =================================================

async def some_completely_runtime_callable():

    return {
        "kind": "runtime_callable"
    }


async def run_scenario():

    # =============================================
    # Filesystem baseline
    # =============================================

    filesystem = await run_flow(
        "area/flow"
    )

    assert_flow_success(
        filesystem
    )

    assert filesystem[
        "filesystem_output"
    ] == {

        "kind":
            "filesystem"
    }

    # =============================================
    # Fully virtual callable flow
    # =============================================

    virtual_callable = (
        PreparedFlow()
        .fset(
            "virtual_node.py",
            some_completely_runtime_callable,
        )
        .fset(
            "consumer_node.py",
            textwrap.dedent(
                '''
                from odyss_ai_flows import *

                @node
                async def consumer_node():

                    value = await nget(
                        "virtual_node"
                    )

                    return {
                        "value": value
                    }
                '''
            ).strip(),
        )
    )

    callable_result = await run_flow(
        virtual_callable
    )

    assert_flow_success(
        callable_result
    )

    # =============================================
    # Node identity derives from path
    # not callable name
    # =============================================

    assert callable_result[
        "virtual_node"
    ] == {

        "kind":
            "runtime_callable"
    }

    # =============================================
    # Callable lookup works
    # =============================================

    assert callable_result[
        some_completely_runtime_callable
    ] == {

        "kind":
            "runtime_callable"
    }

    # =============================================
    # Consumer node worked through nget
    # =============================================

    assert callable_result[
        "consumer_node"
    ] == {

        "value": {

            "kind":
                "runtime_callable"
        }
    }

    # =============================================
    # Fully virtual outputs.json
    # =============================================

    outputs_flow = (
        PreparedFlow()
        .fset(
            "producer.py",
            textwrap.dedent(
                '''
                from odyss_ai_flows import *

                @node
                async def producer():

                    return "value"
                '''
            ).strip(),
        )
        .fset(
            "outputs.json",
            textwrap.dedent(
                '''
                {
                    "include": [

                        "producer"
                    ],

                    "map": {

                        "producer":
                            "mapped_output"
                    }
                }
                '''
            ).strip(),
        )
    )

    outputs_result = await run_flow(
        outputs_flow
    )

    assert_flow_success(
        outputs_result
    )

    # =============================================
    # Mapping works on string lookup
    # =============================================

    assert outputs_result[
        "mapped_output"
    ] == "value"

    # =============================================
    # Old raw node name blocked
    # =============================================

    try:

        outputs_result[
            "producer"
        ]

        raise AssertionError(
            "raw node unexpectedly accessible"
        )

    except KeyError:
        pass

    # =============================================
    # Hybrid filesystem override
    # =============================================

    hybrid = (
        PreparedFlow(
            base_path="area/flow"
        )
        .fset(
            "filesystem_node.py",
            textwrap.dedent(
                '''
                from odyss_ai_flows import *

                @node
                async def replacement_function():

                    return {
                        "kind":
                            "override"
                    }
                '''
            ).strip(),
        )
    )

    hybrid_result = await run_flow(
        hybrid
    )

    assert_flow_success(
        hybrid_result
    )

    # =============================================
    # Same node identity, replaced implementation
    # =============================================

    assert hybrid_result[
        "filesystem_output"
    ] == {

        "kind":
            "override"
    }

    # =============================================
    # Redirected node flow
    # =============================================

    redirected = (
        PreparedFlow()
        .fset(
            "external_node.py",
            Path(
                "shared/external_node.py"
            )
        )
    )

    redirected_result = await run_flow(
        redirected
    )

    assert_flow_success(
        redirected_result
    )

    assert redirected_result[
        "external_node"
    ] == {

        "kind":
            "redirected"
    }

    # =============================================
    # Import-based callable lookup works
    # for redirected node
    # =============================================

    assert redirected_result[
        imported_external_function
    ] == {

        "kind":
            "redirected"
    }

    # =============================================
    # Virtual node with provided_tree
    # =============================================

    virtual_config = (
        PreparedFlow()
        .fset(
            "runtime_node.py",
            textwrap.dedent(
                '''
                from odyss_ai_flows import *

                @node
                async def runtime_node():

                    return {

                        "global_value":
                            await cget(
                                "global_value"
                            ),

                        "node_value":
                            await cget(
                                "node_value"
                            ),

                        "shared":
                            await cget(
                                "shared"
                            ),
                    }
                '''
            ).strip(),
        )
    )

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

            "runtime_node": {

                "name":
                    "runtime_node",

                "path":
                    "runtime_node",

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

    config_result = await run_flow(

        virtual_config,

        provided_tree=provided_tree,
    )

    assert_flow_success(
        config_result
    )

    assert config_result[
        "runtime_node"
    ] == {

        "global_value":
            "provided_global",

        "node_value":
            "provided_node",

        "shared": {

            "x": 1,
            "y": 2,
        },
    }

    # =============================================
    # PreparedFlow.config_tree equivalence
    # =============================================

    prepared_tree = (
        PreparedFlow(
            config_tree=provided_tree
        )
        .fset(
            "runtime_node.py",
            textwrap.dedent(
                '''
                from odyss_ai_flows import *

                @node
                async def runtime_node():

                    return {

                        "global_value":
                            await cget(
                                "global_value"
                            ),

                        "node_value":
                            await cget(
                                "node_value"
                            ),

                        "shared":
                            await cget(
                                "shared"
                            ),
                    }
                '''
            ).strip(),
        )
    )

    prepared_tree_result = await run_flow(
        prepared_tree
    )

    assert_flow_success(
        prepared_tree_result
    )

    assert prepared_tree_result[
        "runtime_node"
    ] == {

        "global_value":
            "provided_global",

        "node_value":
            "provided_node",

        "shared": {

            "x": 1,
            "y": 2,
        },
    }