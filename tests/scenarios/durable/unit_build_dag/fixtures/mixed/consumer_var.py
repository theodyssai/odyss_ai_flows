from odyss_ai_flows import nget, node


@node
async def consumer_var():
    dep = "producer"
    return await nget(dep)
