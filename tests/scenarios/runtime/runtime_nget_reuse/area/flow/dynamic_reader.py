from odyss_ai_flows import *

import tests.scenarios.runtime.runtime_nget_reuse.helpers.shared_state as state


@node
async def dynamic_reader():

    target = (
        "dynamic_dependency_a"
    )

    await nget(
        target
    )

    return {

        "selected":
            target,

        "a_executed":
            state.DYNAMIC_A_EXECUTIONS,

        "b_executed":
            state.DYNAMIC_B_EXECUTIONS,
    }