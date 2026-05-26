from odyss_ai_flows import *


@node
async def repeated_reader():

    a = await nget(
        "shared_dependency"
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