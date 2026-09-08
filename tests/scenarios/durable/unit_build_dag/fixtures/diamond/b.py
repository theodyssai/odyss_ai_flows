from odyss_ai_flows import nget, node


@node
async def b():
    return f"b saw {await nget('a')}"
