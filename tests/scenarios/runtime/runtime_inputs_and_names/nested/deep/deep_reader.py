from odyss_ai_flows import *

from odyss_ai_flows.core.runtime.run_context import (
    get_run_name,
    current_top_run_name,
    current_top_run_id,
)


@node
async def deep_reader():

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
    }