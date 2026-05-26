from odyss_ai_flows import *

import asyncio





@node
async def processor():

    await asyncio.sleep(
        0.01
    )

    intro_result = await nget(
        "intro"
    )

    nested_result = await run_flow(
        "nested_flow"
    )

    await asyncio.sleep(
        0.01
    )

    return {

        "intro":
            intro_result,

        "nested":
            nested_result[
                "nested_message"
            ],
    }