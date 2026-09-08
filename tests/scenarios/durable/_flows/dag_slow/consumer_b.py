from odyss_ai_flows import nget, node


@node
async def consumer_b():
    return f"b:{await nget('slow_producer')}"
