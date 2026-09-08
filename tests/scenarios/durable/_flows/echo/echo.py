from odyss_ai_flows import iget, node


@node
async def echo():
    return iget("message", "")
