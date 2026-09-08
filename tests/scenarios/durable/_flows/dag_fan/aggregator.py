from odyss_ai_flows import nget, node


@node
async def aggregator():
    return await nget("branch_a") + await nget("branch_b") + await nget("branch_c")
