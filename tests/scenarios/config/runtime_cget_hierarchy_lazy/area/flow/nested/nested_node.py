from odyss_ai_flows import *


@node
async def nested_node():

    return {

        "scalar_replace": await cget(
            "scalar_replace"
        ),

        "dict_merge": await cget(
            "dict_merge"
        ),

        "list_replace": await cget(
            "list_replace"
        ),

        "nested": await cget(
            "nested"
        ),
    }