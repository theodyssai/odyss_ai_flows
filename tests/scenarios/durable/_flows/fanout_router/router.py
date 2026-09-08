from odyss_ai_flows import iget, node
from odyss_ai_flows_durable import DurableFlowStep, DurableSubflowOutput

_ECHO = "_flows/echo"


@node
async def router():
    items = iget("items", [])

    return DurableSubflowOutput(
        data={"count": len(items)},
        subflows=[
            DurableFlowStep(flow_name=_ECHO, name=f"item_{i}", inputs={"message": item})
            for i, item in enumerate(items)
        ],
    )
