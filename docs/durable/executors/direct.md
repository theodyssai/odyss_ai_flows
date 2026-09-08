# Direct Execution

"Direct" refers to two related but distinct concepts in the durable plugin: running a flow without any Azure Functions involvement, and running an individual step as an activity rather than a sub-orchestrator within a group plan.

---

# No-Executor Fallback

`run_durable_flow` accepts an optional executor:

```python
from odyss_ai_flows_durable import run_durable_flow

result = await run_durable_flow(
    "path/to/my_flow",
    inputs={"topic": "black holes"},
)
```

When no executor is passed, the call delegates directly to the standard `run_flow` from the core framework. The flow runs in-process as a normal async execution. No Azure Functions app, configuration, or blueprint is required.

This is useful for:

- local development and testing without running an Azure Functions host
- environments where durable execution is not needed
- sharing a single call site across environments by selecting the executor via configuration

The same call with an executor becomes a durable orchestration. Without one, it is a plain in-process run.

---

# DispatchMode.DIRECT

Within group execution (sequence and parallel), each `DurableFlowStep` carries a dispatch mode:

```python
from odyss_ai_flows_durable import DispatchMode, DurableFlowStep

step = DurableFlowStep(
    flow_name="flows/my_flow",
    mode=DispatchMode.DIRECT,
    inputs={"topic": "black holes"},
)
```

`DispatchMode.DIRECT` causes this step to run as a single Azure Functions activity rather than as a full sub-orchestration.

The default mode is `DispatchMode.DURABLE`.

---

# DIRECT vs. DURABLE Dispatch

| | `DURABLE` | `DIRECT` |
|---|---|---|
| Execution unit | sub-orchestrator | activity |
| Per-node intermediate state | persisted | none |
| Replay on failure | from last node checkpoint | from activity start |
| Overhead | higher | lower |
| Per-node retry | yes | no |
| Best for | long-running, failure-prone flows | fast, simple flows |

`DIRECT` dispatch runs the entire flow inside a single activity. The flow executes in-process within that activity. There is no per-node durability — if the activity fails midway through the flow, the whole flow reruns from the beginning on retry.

`DURABLE` dispatch runs each node as its own sub-orchestrator. Intermediate node results are persisted. Individual nodes can be retried without re-running nodes that already completed.

---

# Mixing Modes in a Plan

Steps within the same `DurableFlowPlan` can use different dispatch modes:

```python
from odyss_ai_flows_durable import DispatchMode, DurableFlowPlan, DurableFlowStep

plan = DurableFlowPlan(steps=[
    DurableFlowStep(flow_name="flows/fast_lookup", mode=DispatchMode.DIRECT),
    DurableFlowStep(flow_name="flows/heavy_analysis", mode=DispatchMode.DURABLE),
    DurableFlowStep(flow_name="flows/format_output", mode=DispatchMode.DIRECT),
])
```

Short, fast steps avoid sub-orchestration overhead. Long or failure-prone steps get full per-node durability. Both coexist in the same plan.
