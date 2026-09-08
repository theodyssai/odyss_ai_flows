# Durable execution test scenarios

Tests for the `odyss_ai_flows_durable` plugin. The suite is split in two:

- **infra-free (`direct_flow_execution` + `unit_*`).** Pure contract/logic tests
  (no-executor pass-through, executor dispatch, DAG scan, serialization, config/naming,
  subflow extraction, retry scheduling, event-client URL construction, registration,
  custom protocol injection, telemetry gating/propagation). No Azure host needed. They gate
  only on the plugin being installed, so they **run** on any machine with the plugin and
  **skip cleanly** where it is absent.
- **the remaining scenarios — live.** Orchestration scenarios that drive a running Azure
  Functions host over the Durable Task management API. They declare a `requirements.py`
  that gates on the plugin (hard) **and** a probe of the host port (soft), so with the host
  down they **SKIP** in `auto`/`static` instead of failing.

## Requirement gating (why a down host no longer fails the suite)

Each live scenario ships a `requirements.py`:

```python
from tests.scenarios.durable._shared.host_probe import durable_host_up
from tests.tests_runtime.requirements import requires

REQUIREMENTS = (
    requires()
    .plugin("odyss_ai_flows_durable")               # hard: skip in every mode if absent
    .check("Durable test host ready on :7071", durable_host_up)  # soft config gate
)
```

The probe calls the suite's dedicated `/api/durable-test-health` endpoint to verify host
identity, then checks `/admin/functions/flow_orchestrator` for the actual
`orchestrationTrigger` binding. It is in-process rather than a `.command("python", ...)`
requirement because the project invokes the conda interpreter directly and `python` is not
guaranteed to be on PATH.
`direct_flow_execution` and every `unit_*` scenario use a plugin-only sidecar.

## Running the live half

The host runs from **this directory** (`tests/scenarios/durable/`), which holds its
`function_app.py`, `host.json` and `local.settings.json`. Flow fixtures live under it in
`_flows/` and are referenced relative to it — the core file scanner roots itself at the
process cwd, so the flows must sit beneath the host's working directory.

```bash
# 1. storage emulator (Durable Functions needs AzureWebJobsStorage)
azurite --silent --location /tmp/azurite --debug /tmp/azurite/debug.log

# 2. the Functions host, from tests/scenarios/durable/
func start

# 3. the suite (auto mode), from odyss_ai/
python -m tests.tests_runtime.main
```

With the host **up**, live scenarios run and pass. With it **down**, they SKIP with a
precise reason. `--static` skips every requirement-bearing scenario; `--live` runs them and
lets a missing host fail honestly.

`function_app.py`:
- registers with `RetryOptions(10, 1)` (native node-activity retry disabled) so a
  per-request `DurableRetryPolicy` is the only retry layer the retry scenarios exercise;
- injects a `DurableHttpEventClient(management_url="http://localhost:7071")` for node→node
  signalling. Configuring it **explicitly here** means the suite needs no `global_config.json`
  in the host cwd. The URL is the **bare** host (no `/api`) — the client appends the
  `/runtime/webhooks/durabletask/...` path itself.

A real deployment would instead supply `durable.management_url` (and any other `durable.*`
settings) through its own `global_config.json`; see `docs/durable/quick_start.md`.
