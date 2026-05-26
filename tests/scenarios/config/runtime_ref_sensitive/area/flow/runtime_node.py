from odyss_ai_flows import *


@node
async def runtime_node():

    direct = await cget(
        "direct_secret"
    )

    refed = await cget(
        "ref_secret"
    )

    return {

        "direct": direct,
        "refed": refed,
    }