from pathlib import Path

from odyss_ai_flows import *


@node
async def nested_launcher_b():

    result = await run_flow(

        flow=Path(
            "nested/flow_b"
        ),

        inputs={

            "value": "nested_b",
            "secret": "nested_secret_b",
        },
    )

    return result.outputs[
        "nested_reader_b"
    ]