from odyss_ai_flows import nget, node


@node
async def branch_a():
    return await nget("source") * 2
