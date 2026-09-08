from odyss_ai_flows import *


@node
async def consumer():
    value = await nget("producer")
    return f"{value} via consumer"
