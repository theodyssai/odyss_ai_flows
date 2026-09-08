from odyss_ai_flows import nget, node


@node
async def node_b():
    return f"b saw {await nget('node_a')}"
