from odyss_ai_flows import nget, node


@node
async def branch_b():
    return await nget("source") * 3
