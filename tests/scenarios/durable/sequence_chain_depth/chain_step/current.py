from odyss_ai_flows import *


@node
async def current():
    previous = iget("current")
    suffix = iget("suffix")
    return previous + suffix
