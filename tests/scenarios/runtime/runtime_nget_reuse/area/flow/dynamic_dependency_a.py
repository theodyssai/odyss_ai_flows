import asyncio

from odyss_ai_flows import *

import tests.scenarios.runtime.runtime_nget_reuse.helpers.shared_state as state


@node
async def dynamic_dependency_a():

    state.DYNAMIC_A_EXECUTIONS += 1

    await asyncio.sleep(
        0.02
    )

    return "A"