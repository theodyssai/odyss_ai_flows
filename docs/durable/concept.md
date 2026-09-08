# Durable Plugin

The durable plugin extends odyss_ai_flows with a managed execution layer.

Standard `odyss_ai_flows` execution is in-process. A flow runs, completes, and leaves no persistent state. This is sufficient for most orchestration — it is lightweight, fast, and requires no external infrastructure.

Some systems require more: flows that survive process restarts, nodes that retry independently on failure, orchestration that spans multiple workers, or execution with a persistent audit trail. The **durable plugin** introduces the abstractions needed to enable this without changing flow or node definitions.

---

# The Executor Abstraction

The plugin introduces `DurableFlowExecutor` — an abstract base that determines how a flow is dispatched instead of executing it in-process.

```python
result = await run_flow("my_flow")          # in-process, ephemeral
instance_id = await run_durable_flow("my_flow", executor=executor)  # managed
```

The flow definition is identical in both cases. The executor decides what happens next: it can hand the flow off to a distributed orchestration backend, a queue, a cloud workflow engine, or any other system.

The plugin ships with a built-in executor backed by **Azure Durable Functions**. This is the default implementation, not a fixed dependency. Any backend can be supported by implementing custom `Executor`.

---

# Two Execution Families

The plugin provides two distinct execution families.

**Single flow** — runs one flow through the executor. In the built-in Azure Durable Functions implementation, each node in the flow becomes a separate durable sub-orchestrator, allowing individual node results to be checkpointed and retried independently.

**Group execution** — runs a collection of flows defined as a `DurableFlowPlan`. The flows can execute in sequence or in parallel, with optional retry, input threading between steps, and nested subflow dispatch.

---

# Entry Point

```python
from odyss_ai_flows_durable import run_durable_flow
```

`run_durable_flow` accepts any flow accepted by the core `run_flow`, plus an optional executor:

- Without an executor: delegates to the standard `run_flow` directly.
- With an executor: dispatches through the executor and returns an instance identifier.

This single entry point works across all execution modes and environments.

---

# When to Use This Plugin

Use the durable plugin when:

- flows are long-running and must survive infrastructure restarts
- node failures need automatic retry with backoff
- orchestration spans multiple distributed workers
- you need a persistent audit trail of execution state
- flows coordinate external asynchronous events or human approval

Use standard `run_flow` when:

- execution fits within a single process lifecycle
- flows are short-lived
- you are developing or experimenting locally

The same flow definitions work with both paths.
