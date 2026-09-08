from odyss_ai_flows import *


@node
async def runtime_node():

    direct = await cget(
        "direct_secret"
    )

    refed = await cget(
        "ref_secret"
    )

    wrapped = await cget(
        "wrapped_secret"
    )

    ref_wrapped = await cget(
        "ref_wrapped_secret"
    )

    return {

        "direct": direct,
        "refed": refed,
        "wrapped": wrapped,
        "ref_wrapped": ref_wrapped,
    }