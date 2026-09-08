from odyss_ai_flows import node
from odyss_ai_flows_durable import DurableFlowStep, DurableSubflowOutput

# Each branch dispatches fanout_router, whose own node returns another DurableSubflowOutput
# — this is what exercises 2-level nested subflow dispatch.
_FANOUT = "_flows/fanout_router"
_BRANCHES = [["x1", "x2"], ["y1"]]


@node
async def router():
    return DurableSubflowOutput(
        data={"branch_count": len(_BRANCHES)},
        subflows=[
            DurableFlowStep(flow_name=_FANOUT, name=f"branch_{i}", inputs={"items": items})
            for i, items in enumerate(_BRANCHES)
        ],
    )
