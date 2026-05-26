from odyss_ai_flows import *


@node
async def consumer_node():

    await nget(
        "producer_node"
    )

    return {

        "scalar": await cget(
            "runtime_scalar"
        ),

        "dict": await cget(
            "runtime_dict"
        ),

        "created": await cget(
            "dynamic.created.value"
        ),
    }