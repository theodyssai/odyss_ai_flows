# Quick Start

This page covers the minimum required to run a flow using the durable plugin.

---

# Installation

```bash
pip install odyss_ai_flows_durable
```

---

# Prerequisites

The durable plugin requires:

- an Azure Functions app with Durable Functions enabled
- `azure-functions` and `azure-durable-functions` Python packages installed in the functions environment
- a `global_config.json` in your project root

---

# Required Configuration

Add the following to `global_config.json`:

```json
{
  "durable": {
    "management_url": "https://<your-app>.azurewebsites.net/api",
    "system_key": "<your-durable-system-key>"
  }
}
```

`management_url` is the base URL of the Azure Functions management API. It is used by the plugin to raise inter-orchestrator signals.

`system_key` is the Durable Functions system key required to call the management API in production.

> **Note:** For local development with the Azure Functions Core Tools, the system key is not required:

```json
{
  "durable": {
    "management_url": "http://localhost:7071/api"
  }
}
```

---

# Blueprint Registration

Activities and orchestrators must be registered on an Azure Functions blueprint before the app can execute them.

For single-flow execution:

```python
import azure.durable_functions as df
from odyss_ai_flows_durable import DurableFunctionsExecutor

bp = df.Blueprint()
DurableFunctionsExecutor.register(bp)
```

For both sequence and parallel group execution on the same blueprint:

```python
from odyss_ai_flows_durable import register_durable_support

register_durable_support(bp)
```

`register_durable_support` registers all shared activities once and then registers both group orchestrators. Use it instead of calling each executor's `register()` separately to avoid duplicate activity registrations.

---

# Running a Flow

```python
import azure.functions as func
import azure.durable_functions as df
from odyss_ai_flows_durable import DurableFunctionsExecutor, run_durable_flow

bp = df.Blueprint()
DurableFunctionsExecutor.register(bp)


@bp.route(route="run")
@bp.durable_client_input(client_name="client")
async def http_start(
    req: func.HttpRequest,
    client: df.DurableOrchestrationClient,
) -> func.HttpResponse:
    executor = DurableFunctionsExecutor(client)

    instance_id = await run_durable_flow(
        "path/to/my_flow",
        executor=executor,
        inputs={"topic": "black holes"},
    )

    return client.create_check_status_response(req, instance_id)


app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)
app.register_blueprint(bp)
```

`run_durable_flow` returns the orchestration instance ID. Use it to poll for status or retrieve results through the Durable Functions management API.

Inputs passed via `inputs=` are available inside nodes via `iget()`, exactly as in standard flow execution.

---

# Next Steps

- Executors — choose the right execution model for your use case
- Retry policy — configure automatic retry with backoff
- Telemetry — enable OpenTelemetry tracing across activity boundaries
- Examples — complete, runnable function app examples
