from odyss_ai_flows import nget, node


def producer():  # a function reference, not the string literal "producer"
    ...


@node
async def consumer_fnref():
    return await nget(producer)
