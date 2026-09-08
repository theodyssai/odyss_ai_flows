from odyss_ai_flows import nget, node


@node
async def node_a():
    return f"a saw {await nget('node_b')}"
