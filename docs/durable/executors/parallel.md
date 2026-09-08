# DurableParallelExecutor

`DurableParallelExecutor` runs a list of flows simultaneously.

All steps are dispatched at the same time. The orchestrator waits for all of them to complete before producing results. No step's output is visible to any other step during execution.

---

# DurableFlowPlan

Parallel execution uses the same `DurableFlowPlan` structure as sequence execution:

```python
from odyss_ai_flows_durable import DurableFlowPlan, DurableFlowStep

plan = DurableFlowPlan(steps=[
    DurableFlowStep(flow_name="flows/summarize"),
    DurableFlowStep(flow_name="flows/classify"),
    DurableFlowStep(flow_name="flows/extract_entities"),
])
```

---

# Blueprint Registration

```python
from odyss_ai_flows_durable import DurableParallelExecutor

DurableParallelExecutor.register(bp)
```

If both sequence and parallel execution are needed on the same blueprint, use `register_durable_support` to register shared activities exactly once:

```python
from odyss_ai_flows_durable import register_durable_support

register_durable_support(bp)
```

---

# Running in Parallel

```python
from odyss_ai_flows_durable import DurableParallelExecutor, run_durable_flow

executor = DurableParallelExecutor(client)

instance_id = await run_durable_flow(
    plan,
    executor=executor,
    inputs={"article": "..."},
)
```

---

# Inputs

All steps receive the same `base_inputs`, optionally enriched with each step's own `step.inputs`:

```
Step A receives: {**base_inputs, **step_a.inputs}
Step B receives: {**base_inputs, **step_b.inputs}
Step C receives: {**base_inputs, **step_c.inputs}
```

Unlike sequence execution, no step can see another step's result. Inputs are fixed at the start of the parallel orchestration and do not change between steps.

---

# Results

The final output is a dict keyed by `step.name` or `step.flow_name`:

```python
{
    "flow_results": {
        "summarize": {"summary": "..."},
        "classify":  {"category": "science"},
        "extract_entities": {"entities": [...]},
    }
}
```

---

# Retry

```python
from odyss_ai_flows_durable import DurableRetryPolicy

executor = DurableParallelExecutor(
    client,
    retry_policy=DurableRetryPolicy(attempts=3, backoff=2.0),
)
```

With a retry policy set, all steps are dispatched together in the first attempt. If any steps fail, only those steps are retried on subsequent attempts. Steps that succeeded are not re-executed.

If any step still fails after all attempts are exhausted, the orchestration fails.

---

# Subflows

If any step returns a `DurableSubflowOutput`, subflows from all steps are dispatched together after all parallel steps complete. Subflows from different steps run in parallel within the same `subflows_orchestrator` invocation.

Each step's subflow results are stored under `subflow_results` within that step's entry in `flow_results`.

---

# Sequence vs. Parallel

| | Sequence | Parallel |
|---|---|---|
| Execution order | one step at a time | all steps simultaneously |
| Input threading | each step sees all previous results | all steps see the same initial inputs |
| Step interdependence | supported | not supported |
| Use when | steps depend on each other | steps are independent |
