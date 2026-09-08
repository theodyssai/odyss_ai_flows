from odyss_ai_flows import nget, node


@node
async def step_b():
    return f"step_b got {await nget('step_a')}"
