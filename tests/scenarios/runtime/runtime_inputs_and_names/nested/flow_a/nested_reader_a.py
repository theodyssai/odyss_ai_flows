from pathlib import Path

from odyss_ai_flows import *

from odyss_ai_flows.core.runtime.run_context import (
    get_run_name,
    current_top_run_name,
    current_top_run_id,
)


@node
async def nested_reader_a():

    result = await run_flow(

        flow=Path(
            "nested/deep"
        ),

        inputs={

            "value": "deep_nested",
            "secret": "deep_secret",
        },
    )

    return {

        "value": iget(
            "value"
        ),

        "secret": iget(
            "secret"
        ),

        "run_name":
            get_run_name(),

        "top_run_name":
            current_top_run_name(),

        "top_run_id":
            current_top_run_id(),

        "deep":
            result.outputs[
                "deep_reader"
            ],
    }