import asyncio

from odyss_ai_flows import *


@node
async def delayed_reader():

    a = await nget(
        "shared_dependency"
    )

    await asyncio.sleep(
        0.05
    )

    b = await nget(
        "shared_dependency"
    )

    return {

        "same_identity":

            (
                a["shared_object"]
                is
                b["shared_object"]
            ),
    }