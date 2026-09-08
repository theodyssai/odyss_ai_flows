from odyss_ai_flows import iget, node
from odyss_ai_flows_durable import (
    DurableFlowStep,
    DurableSubflowGroup,
    DurableSubflowOutput,
)

_ECHO = "_flows/echo"


@node
async def router():
    # Two subflow steps with the SAME flow_name in one group. Without distinct names they
    # share a result key (the flow_name) and overwrite each other; with names they are kept
    # apart under subflow_results.
    named = iget("named", False)

    steps = [
        DurableFlowStep(flow_name=_ECHO, name=("a_step" if named else None), inputs={"message": "a"}),
        DurableFlowStep(flow_name=_ECHO, name=("b_step" if named else None), inputs={"message": "b"}),
    ]

    return DurableSubflowOutput(
        data={"named": named},
        groups=[DurableSubflowGroup(key="batch", steps=steps)],
    )
