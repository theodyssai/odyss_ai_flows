# Example: Single Flow, Direct Execution

This example demonstrates running a flow without any Azure Functions infrastructure, and shows how `DispatchMode.DIRECT` works at the step level within a group plan.

---

# Scenario

A two-node flow where one node fetches data and another processes it. We run it in-process using the no-executor fallback.

---

# Flow

```text
flows/process/
├── fetch.py
└── process.py
```

`flows/process/fetch.py`:

```python
from odyss_ai_flows import *


@node
async def fetch():
    source = await iget("source")
    return {"raw": f"data from {source}", "source": source}
```

`flows/process/process.py`:

```python
from odyss_ai_flows import *


@node
async def process():
    data = await nget("fetch")
    return f"processed: {data['raw'].upper()}"
```

---

# Running Without an Executor

```python
import asyncio
from odyss_ai_flows_durable import run_durable_flow


async def main():
    result = await run_durable_flow(
        "flows/process",
        inputs={"source": "database"},
    )
    print(result["process"])


asyncio.run(main())
```

No executor means `run_durable_flow` falls back to the standard `run_flow`. No Azure Functions app, configuration, or blueprint is required.

Output:

```
processed: DATA FROM DATABASE
```

---

# Selecting the Executor via Configuration

A common pattern is to select the executor at the call site based on environment:

```python
import os
import asyncio
import azure.durable_functions as df
from odyss_ai_flows_durable import DurableFunctionsExecutor, run_durable_flow


async def run(client=None):
    executor = DurableFunctionsExecutor(client) if client else None

    result_or_id = await run_durable_flow(
        "flows/process",
        executor=executor,
        inputs={"source": "database"},
    )

    return result_or_id
```

The flow definition and call site are identical in both environments.

---

# DispatchMode.DIRECT in a Group Plan

`DispatchMode.DIRECT` is a per-step setting used within group execution (sequence or parallel). It causes a step to run as an Azure Functions activity rather than as a sub-orchestration.

```python
import azure.functions as func
import azure.durable_functions as df
from odyss_ai_flows_durable import (
    DispatchMode,
    DurableFlowPlan,
    DurableFlowStep,
    DurableSequenceExecutor,
    register_durable_support,
    run_durable_flow,
)

bp = df.Blueprint()
register_durable_support(bp)


@bp.route(route="run-direct")
@bp.durable_client_input(client_name="client")
async def http_start(
    req: func.HttpRequest,
    client: df.DurableOrchestrationClient,
) -> func.HttpResponse:
    plan = DurableFlowPlan(steps=[
        DurableFlowStep(
            flow_name="flows/process",
            mode=DispatchMode.DIRECT,
            inputs={"source": "database"},
        ),
    ])

    executor = DurableSequenceExecutor(client)
    instance_id = await run_durable_flow(plan, executor=executor)

    return client.create_check_status_response(req, instance_id)


app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)
app.register_blueprint(bp)
```

The step runs inside an Azure Functions activity, not as a sub-orchestration. The flow executes in-process within that activity. There is no per-node checkpoint — if the activity fails partway through, the whole flow reruns from the start on retry.

Use `DIRECT` mode for short, fast steps where sub-orchestration overhead is not justified.
