# Example: Single Flow, Durable Execution

This example shows a complete Azure Functions app that runs a single flow using `DurableFunctionsExecutor`. Each node in the flow becomes a separate durable sub-orchestrator.

---

# Flow

```text
flows/analyze/
├── fetch.py
└── analyze.py
```

`flows/analyze/fetch.py`:

```python
from odyss_ai_flows import *


@node
async def fetch():
    topic = await iget("topic")
    return {"topic": topic, "raw_data": f"research data about {topic}"}
```

`flows/analyze/analyze.py`:

```python
from odyss_ai_flows import *


@node
async def analyze():
    fetched = await nget("fetch")
    return {"result": f"analysis of: {fetched['raw_data']}"}
```

---

# global_config.json

For local development:

```json
{
  "durable": {
    "management_url": "http://localhost:7071/api"
  }
}
```

For production:

```json
{
  "durable": {
    "management_url": "https://<your-app>.azurewebsites.net/api",
    "system_key": "<your-durable-system-key>"
  }
}
```

---

# function_app.py

```python
import azure.functions as func
import azure.durable_functions as df
from odyss_ai_flows_durable import DurableFunctionsExecutor, run_durable_flow

bp = df.Blueprint()
DurableFunctionsExecutor.register(bp)


@bp.route(route="analyze")
@bp.durable_client_input(client_name="client")
async def http_start(
    req: func.HttpRequest,
    client: df.DurableOrchestrationClient,
) -> func.HttpResponse:
    topic = req.params.get("topic", "black holes")

    executor = DurableFunctionsExecutor(client)

    instance_id = await run_durable_flow(
        "flows/analyze",
        executor=executor,
        inputs={"topic": topic},
    )

    return client.create_check_status_response(req, instance_id)


app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)
app.register_blueprint(bp)
```

---

# Triggering the Flow

With the Functions app running locally via the Azure Functions Core Tools:

```bash
curl "http://localhost:7071/api/analyze?topic=dark+matter"
```

The response contains status check and result URLs for polling the orchestration.

---

# With Retry Policy

```python
from odyss_ai_flows_durable import DurableRetryPolicy

executor = DurableFunctionsExecutor(
    client,
    retry_policy=DurableRetryPolicy(
        attempts=4,
        initial_delay_seconds=2.0,
        backoff=2.0,
        jitter=0.1,
    ),
)
```

Each node activity retries independently up to `attempts` times. Nodes that already completed are not re-run.

---

# With Custom Instance ID

```python
import uuid

instance_id = await run_durable_flow(
    "flows/analyze",
    executor=executor,
    inputs={"topic": topic},
    instance_id=f"analyze-{uuid.uuid4()}",
)
```

The instance ID propagates to each node sub-orchestrator as `<instance_id>_<node_name>`, making them individually inspectable in the Azure portal.

---

# With Telemetry

Enable in `global_config.json`:

```json
{
  "durable": {
    "management_url": "http://localhost:7071/api",
    "telemetry": {
      "enabled": true
    }
  }
}
```

Configure an OpenTelemetry exporter in your function app bootstrap. Each node activity and the full execution appear as a connected trace in your telemetry backend.
