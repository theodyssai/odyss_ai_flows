from odyss_ai_flows import *


@node
async def nested_consumer_node():

    await nget(
        "producer_node"
    )

    return {

        "scalar": await cget(
            "nested_scalar"
        ),

        "dict": await cget(
            "nested_dict"
        ),
    }