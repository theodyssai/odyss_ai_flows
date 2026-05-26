from odyss_ai_flows import *

import tests.scenarios.runtime.runtime_nget_reuse.helpers.shared_state as state


@node
async def lazy_activation_reader():

    before = (
        state.SHARED_EXECUTIONS
    )

    await nget(
        "shared_dependency"
    )

    after = (
        state.SHARED_EXECUTIONS
    )

    return {

        "before":
            before,

        "after":
            after,
    }