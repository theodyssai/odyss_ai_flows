from odyss_ai_flows import nget, node


@node
async def c():
    return f"c saw {await nget('a')}"
