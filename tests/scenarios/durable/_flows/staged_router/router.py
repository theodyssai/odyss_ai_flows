from odyss_ai_flows import iget, node
from odyss_ai_flows_durable import (
    DurableFlowStep,
    DurableSubflowGroup,
    DurableSubflowGroupConfig,
    DurableSubflowOutput,
)

_ECHO = "_flows/echo"


@node
async def router():
    items = iget("items", [])

    return DurableSubflowOutput(
        data={"count": len(items)},
        groups=[
            DurableSubflowGroup(
                key="fetch",
                steps=[
                    DurableFlowStep(flow_name=_ECHO, name=f"fetch_{i}", inputs={"message": item})
                    for i, item in enumerate(items)
                ],
                config=DurableSubflowGroupConfig(max_concurrent=2),
            ),
            DurableSubflowGroup(
                key="notify",
                steps=[DurableFlowStep(flow_name=_ECHO, name="notify", inputs={"message": "done"})],
                config=DurableSubflowGroupConfig(wait_before_seconds=1.0),
            ),
        ],
    )
