import asyncio

from pathlib import Path

from odyss_ai_flows import *


@node
async def concurrent_launcher():

    async def run_nested(
        value: str,
    ):

        result = await run_flow(

            flow=Path(
                "nested/concurrent"
            ),

            inputs={

                "value": value,
                "secret": f"secret::{value}",
            },
        )

        return result.outputs[
            "concurrent_reader"
        ]

    return await asyncio.gather(

        run_nested(
            "concurrent_1"
        ),

        run_nested(
            "concurrent_2"
        ),
    )