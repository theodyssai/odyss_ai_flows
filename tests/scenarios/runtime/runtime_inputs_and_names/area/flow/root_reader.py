from odyss_ai_flows import *

from odyss_ai_flows.core.runtime.run_context import (
    get_run_name,
    current_top_run_name,
    current_top_run_id,
)


@node
async def root_reader():

    value = iget(
        "value"
    )

    secret = iget(
        "secret"
    )

    missing = iget(
        "missing",
        default=123,
    )

    tuple_values = iget(

        ["value", "missing2"],

        default=[
            None,
            999,
        ]
    )

    return {

        "value": value,

        "secret": secret,

        "defaults": {

            "single": missing,

            "tuple": list(
                tuple_values
            ),
        },

        "run_name":
            get_run_name(),

        "top_run_name":
            current_top_run_name(),

        "top_run_id":
            current_top_run_id(),
    }