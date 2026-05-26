from odyss_ai_flows import *

import tests.scenarios.runtime.runtime_nested_flows.helpers.shared_state as state


@node
async def lazy_summary_node():

    # =====================================
    # Explicit synchronization barrier
    # =====================================

    await nget(
        "orchestrator_node"
    )

    await nget(
        "propagation_node"
    )

    await nget(
        "sibling_node"
    )

    return {

        "execution_count":
            state.LAZY_EXECUTIONS,
    }