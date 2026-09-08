from odyss_ai_flows import nget, node


@node
async def consumer_literal():
    return await nget("producer")
