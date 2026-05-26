from odyss_ai_flows import *

from tests.scenarios.runtime.runtime_import_access.area.flow.node_a import (
    some_completely_irrelevant_function_name,
)


@node
async def another_irrelevant_function_name():

    value = await nget(
        some_completely_irrelevant_function_name
    )

    return "value_b"