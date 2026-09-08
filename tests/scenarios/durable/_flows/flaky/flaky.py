import os

from odyss_ai_flows import iget, node

# Core re-execs node modules on every run_flow, so a module-level counter would reset each
# attempt; os.environ is process-global and survives across an activity's retries.
_PREFIX = "ODYSS_DURABLE_TEST_FLAKY_"


@node
async def flaky():
    run_id = iget("run_id", "default")
    fail_times = int(iget("fail_times", 0))

    key = _PREFIX + str(run_id)
    attempt = int(os.environ.get(key, "0")) + 1
    os.environ[key] = str(attempt)

    if attempt <= fail_times:
        raise RuntimeError(f"flaky: forced failure on attempt {attempt} (run_id={run_id})")

    return {"attempt": attempt, "run_id": run_id}
