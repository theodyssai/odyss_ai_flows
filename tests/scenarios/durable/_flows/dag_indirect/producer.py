from odyss_ai_flows import node


@node
async def producer():
    return "produced"
