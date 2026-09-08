from odyss_ai_flows import nget, node


@node
async def branch_c():
    return await nget("source") * 4
