from odyss_ai_flows import *


@node
async def runtime_node():

    return {

        "global_value": await cget(
            "global_value"
        ),

        "node_value": await cget(
            "node_value"
        ),

        "shared": await cget(
            "shared"
        ),
    }