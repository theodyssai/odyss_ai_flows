from odyss_ai_flows import nget, node


@node
async def d():
    return f"d saw {await nget('b')} and {await nget('c')}"
