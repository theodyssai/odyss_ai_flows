from odyss_ai_flows import nget, node


@node
async def consumer_a():
    return f"a:{await nget('slow_producer')}"
