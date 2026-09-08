from odyss_ai_flows import iget, node
from odyss_ai_flows_durable import (
    DurableFlowStep,
    DurableSubflowGroup,
    DurableSubflowOutput,
)

_ECHO = "_flows/echo"


@node
async def router():
    # Emits the same two echo subflows either as a flat `subflows` list or as one explicit
    # group keyed "__default__". The docs claim a flat list is just a single implicit default
    # group, so both forms must produce an identical subflow_results shape.
    form = iget("form", "flat")
    steps = [
        DurableFlowStep(flow_name=_ECHO, name=f"item_{i}", inputs={"message": m})
        for i, m in enumerate(["a", "b"])
    ]

    if form == "group":
        return DurableSubflowOutput(
            data={"form": form},
            groups=[DurableSubflowGroup(key="__default__", steps=steps)],
        )

    return DurableSubflowOutput(data={"form": form}, subflows=steps)
