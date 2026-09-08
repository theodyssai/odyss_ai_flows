import os

from odyss_ai_flows import iget, nget, node

_PREFIX = "ODYSS_DURABLE_TEST_FINISH_"


@node
async def finish():
    upstream = await nget("effect")
    run_id = iget("run_id", "default")
    fail_times = int(iget("fail_times", 0))

    key = _PREFIX + str(run_id)
    attempt = int(os.environ.get(key, "0")) + 1
    os.environ[key] = str(attempt)

    if attempt <= fail_times:
        raise RuntimeError(
            f"finish: forced failure on attempt {attempt} (run_id={run_id})"
        )

    return {
        "attempt": attempt,
        "effect_count": upstream["effect_count"],
    }
