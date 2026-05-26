from odyss_ai_flows import *

from odyss_ai_flows.core.runtime.run_context import (
    get_run_name,
    current_top_run_name,
)


@node
async def final_value():

    return {

        "value":
            "nested_b",

        "run_name":
            get_run_name(),

        "top_name":
            current_top_run_name(),
    }