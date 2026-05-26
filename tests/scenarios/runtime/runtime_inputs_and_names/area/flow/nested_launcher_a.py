from pathlib import Path

from odyss_ai_flows import *


@node
async def nested_launcher_a():

    result = await run_flow(

        flow=Path(
            "nested/flow_a"
        ),

        inputs={

            "value": "nested_a",
            "secret": "nested_secret_a",
        },
    )

    return result.outputs[
        "nested_reader_a"
    ]