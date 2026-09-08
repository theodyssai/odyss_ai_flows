# Example: Group of Flows, Parallel

This example runs three flows simultaneously. All flows share the same initial inputs and execute independently of each other.

---

# Flows

```text
flows/
├── summarize/
│   └── summarize.py
├── classify/
│   └── classify.py
└── extract/
    └── extract.py
```

`flows/summarize/summarize.py`:

```python
from odyss_ai_flows import *


@node
async def summarize():
    article = await iget("article")
    return {"summary": f"Summary of: {article[:40]}..."}
```

`flows/classify/classify.py`:

```python
from odyss_ai_flows import *


@node
async def classify():
    article = await iget("article")
    return {"category": "science", "confidence": 0.91}
```

`flows/extract/extract.py`:

```python
from odyss_ai_flows import *


@node
async def extract():
    article = await iget("article")
    return {"entities": ["black hole", "event horizon", "singularity"]}
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
    DurableParallelExecutor,
    register_durable_support,
    run_durable_flow,
)

bp = df.Blueprint()
register_durable_support(bp)


@bp.route(route="enrich")
@bp.durable_client_input(client_name="client")
async def http_start(
    req: func.HttpRequest,
    client: df.DurableOrchestrationClient,
) -> func.HttpResponse:
    body = req.get_json()
    article = body.get("article", "")

    plan = DurableFlowPlan(steps=[
        DurableFlowStep(flow_name="flows/summarize"),
        DurableFlowStep(flow_name="flows/classify"),
        DurableFlowStep(flow_name="flows/extract"),
    ])

    executor = DurableParallelExecutor(client)

    instance_id = await run_durable_flow(
        plan,
        executor=executor,
        inputs={"article": article},
    )

    return client.create_check_status_response(req, instance_id)


app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)
app.register_blueprint(bp)
```

---

# Triggering the Flow

```bash
curl -X POST "http://localhost:7071/api/enrich" \
  -H "Content-Type: application/json" \
  -d '{"article": "Black holes are regions of spacetime..."}'
```

---

# Input Isolation

All three flows receive the same inputs:

```python
{"article": "Black holes are regions of spacetime..."}
```

No flow can see another flow's output during execution. Inputs are fixed at the start of the parallel orchestration.

---

# Final Result Shape

```json
{
  "flow_results": {
    "summarize": {"summary": "Summary of: Black holes are regions of s..."},
    "classify":  {"category": "science", "confidence": 0.91},
    "extract":   {"entities": ["black hole", "event horizon", "singularity"]}
  }
}
```

---

# With Retry

```python
from odyss_ai_flows_durable import DurableRetryPolicy

executor = DurableParallelExecutor(
    client,
    retry_policy=DurableRetryPolicy(attempts=3, backoff=2.0),
)
```

If any flow fails, only the failed flows are retried. Successful flows are not re-executed.

---

# Mixing Dispatch Modes

```python
from odyss_ai_flows_durable import DispatchMode

plan = DurableFlowPlan(steps=[
    DurableFlowStep(flow_name="flows/summarize"),
    DurableFlowStep(flow_name="flows/classify", mode=DispatchMode.DIRECT),
    DurableFlowStep(flow_name="flows/extract"),
])
```

`DIRECT` steps run as activities without per-node checkpointing. Use it for steps that are fast and unlikely to fail partway through.
