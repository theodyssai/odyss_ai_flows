from odyss_ai_flows import *

from odyss_ai_flows.core.config.context import (
    config,
)


@node
async def producer_node():

    initial_scalar = await config.get(

        "runtime_scalar",

        node_scope=(
            "area/flow/consumer_node"
        ),
    )

    initial_dict = await config.get(

        "runtime_dict",

        node_scope=(
            "area/flow/consumer_node"
        ),
    )

    # ============================================
    # Inject override into consumer node
    # ============================================

    config.override(

        "area/flow/consumer_node",

        "runtime_scalar",

        "consumer_overridden",
    )

    config.override(

        "area/flow/consumer_node",

        "runtime_dict.b",

        2,
    )

    config.override(

        "area/flow/consumer_node",

        "dynamic.created.value",

        123,
    )

    # ============================================
    # Inject override into nested node
    # ============================================

    config.override(

        "area/flow/nested/nested_consumer_node",

        "nested_scalar",

        "nested_overridden",
    )

    config.override(

        "area/flow/nested/nested_consumer_node",

        "nested_dict.y",

        20,
    )

    return {

        "initial_consumer_scalar":
            initial_scalar,

        "initial_consumer_dict":
            initial_dict,
    }