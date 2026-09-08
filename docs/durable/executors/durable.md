# DurableFunctionsExecutor

`DurableFunctionsExecutor` runs a single flow as a durable orchestration on Azure Durable Functions.

Each node in the flow becomes a separate sub-orchestrator. Node results are persisted through Azure Durable Functions' event sourcing mechanism. If the process restarts mid-execution, the orchestration replays from its last checkpoint without re-executing already-completed nodes.

---

# DAG Construction

When `start()` is called, the executor scans the flow directory and builds a dependency graph (DAG) from the node files.

Dependencies are extracted statically:

- In `.py` files: by parsing the AST for `nget("name")` calls.
- In `.jinja2` files: by matching the `nget(...)` pattern with a regular expression.

No import or execution takes place during DAG construction. The DAG is serialized into the orchestration input and used by the orchestrator to schedule nodes and wire dependency events.

---

# Execution Model

The orchestrator schedules every node as a sub-orchestrator simultaneously. Each node sub-orchestrator:

1. Waits for external events from each of its upstream dependencies.
2. Once all upstream results arrive, runs the node inside an activity.
3. Raises events carrying its result to all downstream node sub-orchestrators.

Nodes with no dependencies execute immediately. Nodes with dependencies suspend until their upstream signals arrive. This mirrors the in-process `nget()` suspension model, lifted onto durable state.

---

# Blueprint Registration

All activities and orchestrators must be registered on an Azure Functions blueprint before the app can execute them.

```python
import azure.durable_functions as df
from odyss_ai_flows_durable import DurableFunctionsExecutor

bp = df.Blueprint()
DurableFunctionsExecutor.register(bp)
```

`register()` registers the following on the blueprint:

| Name | Type | Purpose |
|---|---|---|
| `flow_orchestrator` | orchestration trigger | coordinates the full DAG; schedules all node sub-orchestrators |
| `node_orchestrator` | orchestration trigger | waits for upstream signals, runs node activity, signals downstream |
| `node_activity` | activity trigger | executes a single node within the flow |
| `signal_event` | activity trigger | raises a dependency event on a target node orchestration |
| `get_jitter_factor_activity` | activity trigger | computes retry jitter outside orchestrator code |

---

# Creating an Executor

```python
from odyss_ai_flows_durable import DurableFunctionsExecutor, DurableRetryPolicy

executor = DurableFunctionsExecutor(
    client,
    retry_policy=DurableRetryPolicy(attempts=4, backoff=2.0),
)
```

`client` is a `df.DurableOrchestrationClient` injected by the Azure Functions durable client binding.

`retry_policy` is optional. When set, each node activity retries according to the policy before the overall orchestration fails.

---

# Custom RetryOptions

`df.RetryOptions` controls how the sub-orchestrator scheduling layer retries on infrastructure failures, independently of `DurableRetryPolicy`:

```python
DurableFunctionsExecutor.register(
    bp,
    retry_options=df.RetryOptions(
        first_retry_interval_in_milliseconds=5000,
        max_number_of_attempts=3,
    ),
)
```

When no `retry_options` are passed, a default of `RetryOptions(10, 1)` is used (10ms first interval, 1 attempt).

---

# Custom Event Client

Dependency signals are sent between node sub-orchestrators via HTTP by default, using `DurableHttpEventClient`. This client reads `durable.management_url` and `durable.system_key` from `global_config.json`.

To provide a custom event client, implement the `DurableEventClient` protocol and pass it to `register()`:

```python
from odyss_ai_flows_durable import DurableEventClient

class MyEventClient:
    async def raise_event(self, instance_id: str, event_name: str, data) -> None:
        ...

DurableFunctionsExecutor.register(bp, event_client=MyEventClient())
```

---

# Instance IDs

Each node sub-orchestrator receives a deterministic instance ID:

```
<parent_instance_id>_<node_name>
```

If no parent instance ID was provided, the node name alone is used. This naming scheme makes individual node orchestrations inspectable in the Azure portal and via the management API.

A custom instance ID for the top-level orchestration can be passed to `run_durable_flow`:

```python
instance_id = await run_durable_flow(
    "path/to/my_flow",
    executor=executor,
    instance_id="my-run-001",
)
```
