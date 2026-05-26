import asyncio

from odyss_ai_flows import *

import tests.scenarios.runtime.runtime_nget_reuse.helpers.shared_state as state


@node
async def shared_dependency():

    state.SHARED_EXECUTIONS += 1

    await asyncio.sleep(
        0.05
    )

    return {

        "execution_count":
            state.SHARED_EXECUTIONS,

        "shared_object":
            state.SHARED_OBJECT,
    }