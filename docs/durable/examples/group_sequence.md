# Example: Group of Flows, Sequence

This example runs three flows in sequence. Each flow receives the outputs of all preceding flows merged into its inputs.

---

# Flows

```text
flows/
├── gather/
│   └── gather.py
├── process/
│   └── process.py
└── report/
    └── report.py
```

`flows/gather/gather.py`:

```python
from odyss_ai_flows import *


@node
async def gather():
    source = await iget("source")
    return {"records": [f"item_a from {source}", f"item_b from {source}"], "count": 2}
```

`flows/process/process.py`:

```python
from odyss_ai_flows import *


@node
async def process():
    records = await iget("records")
    return {"processed": [r.upper() for r in records]}
```

`flows/report/report.py`:

```python
from odyss_ai_flows import *


@node
async def report():
    processed = await iget("processed")
    count = await iget("count")
    return {"report": f"Processed {count} record(s): {processed}"}
```

---

# global_config.json

```json
{
  "durable": {
    "management_url": "http://localhost:7071/api"
  }
}
```

---

# function_app.py

```python
import azure.functions as func
import azure.durable_functions as df
from odyss_ai_flows_durable import (
    DurableFlowPlan,
    DurableFlowStep,
    DurableSequenceExecutor,
    register_durable_support,
    run_durable_flow,
)

bp = df.Blueprint()
register_durable_support(bp)


@bp.route(route="pipeline")
@bp.durable_client_input(client_name="client")
async def http_start(
    req: func.HttpRequest,
    client: df.DurableOrchestrationClient,
) -> func.HttpResponse:
    plan = DurableFlowPlan(steps=[
        DurableFlowStep(flow_name="flows/gather",  name="gather"),
        DurableFlowStep(flow_name="flows/process", name="process"),
        DurableFlowStep(flow_name="flows/report",  name="report"),
    ])

    executor = DurableSequenceExecutor(client)

    instance_id = await run_durable_flow(
        plan,
        executor=executor,
        inputs={"source": "database"},
    )

    return client.create_check_status_response(req, instance_id)


app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)
app.register_blueprint(bp)
```

---

# Input Threading

Inputs available to each step after result merging:

| Step | Available inputs |
|---|---|
| `gather` | `source` |
| `process` | `source`, `records`, `count` |
| `report` | `source`, `records`, `count`, `processed` |

Each step's result is deep-merged into the running base inputs before the next step starts. Keys from earlier steps remain available unless overwritten by a later step.

---

# Final Result Shape

```json
{
  "flow_results": {
    "gather":  {"records": ["item_a from database", "item_b from database"], "count": 2},
    "process": {"processed": ["ITEM_A FROM DATABASE", "ITEM_B FROM DATABASE"]},
    "report":  {"report": "Processed 2 record(s): ['ITEM_A FROM DATABASE', 'ITEM_B FROM DATABASE']"}
  }
}
```

---

# With Retry

```python
from odyss_ai_flows_durable import DurableRetryPolicy

executor = DurableSequenceExecutor(
    client,
    retry_policy=DurableRetryPolicy(attempts=3, backoff=2.0),
)
```

Each step retries independently. Earlier steps that completed successfully are not re-run when a later step fails.

---

# Mixing Dispatch Modes

Steps that are fast and simple can use `DIRECT` mode to avoid sub-orchestration overhead:

```python
from odyss_ai_flows_durable import DispatchMode

plan = DurableFlowPlan(steps=[
    DurableFlowStep(flow_name="flows/gather",  name="gather",  mode=DispatchMode.DIRECT),
    DurableFlowStep(flow_name="flows/process", name="process"),
    DurableFlowStep(flow_name="flows/report",  name="report",  mode=DispatchMode.DIRECT),
])
```

`DIRECT` steps run as activities. `DURABLE` steps run as sub-orchestrations with per-node checkpointing.
