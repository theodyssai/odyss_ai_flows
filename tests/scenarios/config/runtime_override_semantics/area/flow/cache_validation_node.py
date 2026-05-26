from odyss_ai_flows import *

from odyss_ai_flows.core.config.context import (
    config,
)


@node
async def cache_validation_node():

    await nget(
        "consumer_node"
    )

    before = await cget(
        "runtime_scalar"
    )

    config.override(

        "area/flow/cache_validation_node",

        "runtime_scalar",

        "consumer_second_override",
    )

    after = await cget(
        "runtime_scalar"
    )

    return {

        "before": before,
        "after": after,
    }