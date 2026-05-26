import asyncio

from odyss_ai_flows import *

import tests.scenarios.runtime.runtime_nested_flows.helpers.shared_state as state


@node
async def lazy_nested_node():

    state.LAZY_EXECUTIONS += 1

    await asyncio.sleep(
        0.02
    )

    return "lazy"