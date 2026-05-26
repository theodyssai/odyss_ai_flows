from odyss_ai_flows import *


@node
async def summary_node():

    await nget(
        "producer_a"
    )

    await nget(
        "hidden_internal"
    )

    return "summary"