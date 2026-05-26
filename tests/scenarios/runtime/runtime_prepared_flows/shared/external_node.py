from odyss_ai_flows import *


@node
async def imported_external_function():

    return {

        "kind":
            "redirected"
    }


async def external_node():

    return await imported_external_function()