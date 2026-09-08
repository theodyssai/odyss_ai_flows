# DurableSequenceExecutor

`DurableSequenceExecutor` runs a list of flows one after another.

After each step completes, its result is deep-merged into the shared inputs. The next step receives all inputs from the previous step in addition to the original base inputs. This allows each flow in the sequence to build on the outputs of all preceding flows.

---

# DurableFlowPlan

Sequence execution requires a `DurableFlowPlan`:

```python
from odyss_ai_flows_durable import DurableFlowPlan, DurableFlowStep

plan = DurableFlowPlan(steps=[
    DurableFlowStep(flow_name="flows/fetch_data"),
    DurableFlowStep(flow_name="flows/analyze"),
    DurableFlowStep(flow_name="flows/summarize"),
])
```

---

# DurableFlowStep Fields

| Field | Type | Default | Description |
|---|---|---|---|
| `flow_name` | `str` | required | Path or name of the flow to execute |
| `mode` | `DispatchMode` | `DURABLE` | `DURABLE` or `DIRECT` — see executor/direct |
| `name` | `str \| None` | `None` | Optional result key override |
| `inputs` | `dict` | `{}` | Additional inputs for this step only |

---

# Blueprint Registration

```python
from odyss_ai_flows_durable import DurableSequenceExecutor

DurableSequenceExecutor.register(bp)
```

This registers the sequence orchestrator and all shared activities including node execution, signaling, direct flow dispatch, virtual span construction, and jitter computation.

If both sequence and parallel execution are needed on the same blueprint, use `register_durable_support` to register shared activities exactly once:

```python
from odyss_ai_flows_durable import register_durable_support

register_durable_support(bp)
```

---

# Running a Sequence

```python
from odyss_ai_flows_durable import DurableSequenceExecutor, run_durable_flow

executor = DurableSequenceExecutor(client)

instance_id = await run_durable_flow(
    plan,
    executor=executor,
    inputs={"dataset": "q1_2025"},
)
```

---

# Result Threading

After each step completes, its result is deep-merged into the running `base_inputs`. The next step receives the enriched inputs.

Example with three steps and `inputs={"dataset": "q1_2025"}`:

```
Step 1: flows/fetch_data
  receives:  {"dataset": "q1_2025"}
  returns:   {"records": [...], "count": 42}

Step 2: flows/analyze
  receives:  {"dataset": "q1_2025", "records": [...], "count": 42}
  returns:   {"insights": [...]}

Step 3: flows/summarize
  receives:  {"dataset": "q1_2025", "records": [...], "count": 42, "insights": [...]}
  returns:   {"summary": "..."}
```

Keys from earlier steps remain available for all subsequent steps unless overwritten by a later result.

The merge is a deep merge: nested dicts are merged key-by-key rather than replaced.

---

# Per-Step Inputs

`step.inputs` are merged on top of the running base inputs for that step only. They do not persist to subsequent steps unless the step's result also contains those keys.

```python
DurableFlowStep(
    flow_name="flows/analyze",
    inputs={"mode": "deep"},
)
```

The next step does not receive `mode: deep` unless `flows/analyze` returns it.

---

# Step Result Keys

By default, each step's result is stored in the final output under `flow_name`:

```python
{
    "flow_results": {
        "fetch_data": {...},
        "analyze": {...},
        "summarize": {...},
    }
}
```

Use `name` to override the key:

```python
DurableFlowStep(flow_name="flows/analyze", name="analysis")
```

Result: `{"flow_results": {"analysis": {...}}}`

---

# Retry

```python
from odyss_ai_flows_durable import DurableRetryPolicy

executor = DurableSequenceExecutor(
    client,
    retry_policy=DurableRetryPolicy(attempts=3, backoff=2.0),
)
```

Each step retries independently according to the policy. Earlier steps that completed successfully are not re-run when a later step fails and retries.

---

# Subflows

If a step returns a `DurableSubflowOutput`, the sequence pauses after that step, dispatches the declared subflows in parallel, and waits for them to complete before continuing to the next step.

The step result (including `subflow_results`) is deep-merged into `base_inputs` as usual, making subflow results available to all subsequent steps.

See subflows documentation for details.
