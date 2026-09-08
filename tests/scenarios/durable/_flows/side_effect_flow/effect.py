import os

from odyss_ai_flows import iget, node

_PREFIX = "ODYSS_DURABLE_TEST_EFFECT_"


@node
async def effect():
    run_id = iget("run_id", "default")
    key = _PREFIX + str(run_id)
    count = int(os.environ.get(key, "0")) + 1
    os.environ[key] = str(count)
    return {"effect_count": count}
