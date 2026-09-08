# Subflows

A node can instruct the orchestrator to spawn additional flows after it completes.

This is done by returning a `DurableSubflowOutput` instead of a plain value. The node does not execute the subflows itself — it returns a descriptor, and the orchestrator dispatches them.

This pattern allows a flow to produce dynamic follow-up work. The set of subsequent flows is determined at runtime by the node's own logic rather than being fixed in the plan.

---

# DurableSubflowOutput

```python
from odyss_ai_flows import *
from odyss_ai_flows_durable import DurableFlowStep, DurableSubflowOutput


@node
async def router():
    topic = await iget("topic")
    items = await iget("items")

    return DurableSubflowOutput(
        data={"topic": topic, "count": len(items)},
        subflows=[
            DurableFlowStep(flow_name="flows/process", inputs={"item": item})
            for item in items
        ],
    )
```

`data` is the node's own result. Downstream nodes receive it via `nget()` as usual.

`subflows` is a flat list of flows to dispatch after this node completes. All of them are dispatched together, in one batch, with no concurrency limit — this is the simplest form of subflow dispatch.

For staged dispatch with concurrency limits, ordering, or wait timers, use `groups` instead — see below.

---

# Grouped, Staged Dispatch

`groups` declares one or more `DurableSubflowGroup`s instead of a flat list. Groups run as ordered stages: the next group doesn't start until the previous one (including any wait timers) has fully completed.

```python
from odyss_ai_flows import *
from odyss_ai_flows_durable import (
    DurableFlowStep,
    DurableSubflowGroup,
    DurableSubflowGroupConfig,
    DurableSubflowOutput,
)


@node
async def router():
    items = await iget("items")

    return DurableSubflowOutput(
        data={"count": len(items)},
        groups=[
            DurableSubflowGroup(
                key="fetch",
                steps=[
                    DurableFlowStep(flow_name="flows/fetch", name=f"fetch_{i}", inputs={"item": item})
                    for i, item in enumerate(items)
                ],
                config=DurableSubflowGroupConfig(max_concurrent=5),
            ),
            DurableSubflowGroup(
                key="notify",
                steps=[DurableFlowStep(flow_name="flows/notify")],
                config=DurableSubflowGroupConfig(wait_before_seconds=2.0),
            ),
        ],
    )
```

Here, all `fetch_*` steps run first, at most 5 concurrently. Only once every `fetch` step has completed does the orchestrator wait 2 seconds and then dispatch `notify`.

`groups` and `subflows` can be used independently. A plain `subflows` list is equivalent to a single group with no concurrency limit and no waits — it is not a separate code path, just the default configuration of one implicit group.

---

# DurableSubflowGroupConfig

| Field | Default | Description |
|---|---|---|
| `max_concurrent` | unlimited | Dispatch at most this many steps from the group at a time. Later batches within the group only start once the previous batch's `task_all` completes. |
| `wait_before_seconds` | `0.0` | Durable timer delay before the group's first batch is dispatched. |
| `wait_after_seconds` | `0.0` | Durable timer delay after the group's last batch completes, before the next group starts. |
| `skip_group_output` | `False` | If `True`, the group's results are still recorded in `subflow_results`, but are not merged forward into later groups' inputs. |

A field left unset on a group's `config` falls back to the output's `default_group_config` (if set), then to the defaults above:

```python
DurableSubflowOutput(
    data=...,
    default_group_config=DurableSubflowGroupConfig(max_concurrent=10),
    groups=[
        DurableSubflowGroup(key="a", steps=[...]),  # inherits max_concurrent=10
        DurableSubflowGroup(
            key="b",
            steps=[...],
            config=DurableSubflowGroupConfig(max_concurrent=2),  # overrides to 2
        ),
    ],
)
```

---

# DurableFlowStep in Subflows

Each subflow is a `DurableFlowStep`. The same fields apply as in group execution plans:

| Field | Description |
|---|---|
| `flow_name` | Path or name of the flow to run |
| `mode` | `DURABLE` (default) or `DIRECT` |
| `name` | Optional key for this subflow in the results |
| `inputs` | Additional inputs merged on top of the running inputs |

---

# How the Orchestrator Handles It

When a step result contains a serialized `DurableSubflowOutput`, the orchestrator:

1. Records `data` as the step's result, available to downstream nodes.
2. Normalizes the declaration into one or more `DurableSubflowGroup`s — a flat `subflows` list becomes a single implicit group with no concurrency limit and no waits.
3. Runs the groups one at a time, in declared order. Within a group, steps are dispatched in `max_concurrent`-sized batches (or all at once if unset), with optional `wait_before_seconds` / `wait_after_seconds` timers around the group.
4. Waits for the full group sequence — and any subflows-of-subflows it triggers — to complete before finalizing the step.

If multiple nodes in the same step each return a flat `subflows` list (no `groups`), they're still combined into one implicit group and dispatched together, exactly as before grouping existed.

---

# Subflow Results

Subflow results are nested one level by group key:

```python
{
    "topic": "black holes",
    "count": 3,
    "subflow_results": {
        "fetch": {
            "fetch_0": {...},
            "fetch_1": {...},
        },
        "notify": {
            "notify": {...},
        },
    },
}
```

A plain `subflows` list (no `groups`) is wrapped under the implicit `"__default__"` key:

```python
{
    "subflow_results": {
        "__default__": {
            "process": {...},
        },
    },
}
```

Within a group, steps that share the same `flow_name` and no `name` overwrite each other in the results. Use `name` to distinguish them:

```python
DurableFlowStep(flow_name="flows/process", name="process_item_0", inputs={"item": items[0]}),
DurableFlowStep(flow_name="flows/process", name="process_item_1", inputs={"item": items[1]}),
```

---

# Inputs and Result Propagation

Each subflow step receives the **running inputs** at the moment its batch is scheduled, with `step.inputs` deep-merged on top. The merge is recursive: nested dicts are merged key-by-key rather than replaced.

Running inputs start as the parent step's inputs and accumulate as dispatch proceeds:

- After each batch within a group, that batch's results are deep-merged in before the next batch in the same group is scheduled — a later batch can see an earlier batch's output.
- After a group finishes, its results are deep-merged into the inputs for the next group — unless that group has `skip_group_output=True`, in which case its results still appear in `subflow_results` but are not carried forward.
- Steps within the same batch never see each other's results — they run concurrently and are all scheduled before any of them completes.

---

# Nested Subflows

Subflows can themselves return `DurableSubflowOutput`, triggering further nested subflows — flat or grouped, independently of how the parent level was declared.

The orchestrator handles this recursively through the same `subflows_orchestrator`, tracking a depth counter on each level. There is no hardcoded depth limit, but each nesting level adds replay overhead.

---

# Result Threading in Sequence

In sequence execution, if a step returns a `DurableSubflowOutput`, the final step result (including the group-nested `subflow_results`) is deep-merged into `base_inputs` before the next step starts. The next step can access it via `iget("subflow_results")`, then index by group key (or `"__default__"` for a flat declaration).

---

# When to Use Subflows

Use a flat `subflows` list when the set of follow-up flows is dynamic but homogeneous — dispatch them all together, no staging required.

Use `groups` when you need staged dispatch: a concurrency cap to avoid overwhelming a downstream system, a delay between stages, or a stage whose output shouldn't leak into the next one (`skip_group_output`).

If the set of flows is known in advance and doesn't depend on a node's runtime logic, define them directly in a `DurableFlowPlan` passed to a sequence or parallel executor instead.
