import asyncio

from odyss_ai_flows import *


@node
async def concurrent_reader():

    a, b, c = await asyncio.gather(

        nget(
            "shared_dependency"
        ),

        nget(
            "shared_dependency"
        ),

        nget(
            "shared_dependency"
        ),
    )

    return {

        "same_identity":

            (
                a["shared_object"]
                is
                b["shared_object"]
                is
                c["shared_object"]
            ),
    }