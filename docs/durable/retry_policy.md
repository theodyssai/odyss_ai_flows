# Retry Policy

The durable plugin includes a built-in retry mechanism for both single-flow and group execution.

---

# DurableRetryPolicy

```python
from odyss_ai_flows_durable import DurableRetryPolicy

policy = DurableRetryPolicy(
    attempts=3,
    initial_delay_seconds=1.0,
    backoff=2.0,
    jitter=0.2,
)
```

| Field | Default | Description |
|---|---|---|
| `attempts` | `3` | Total number of attempts including the first |
| `initial_delay_seconds` | `1.0` | Delay in seconds before the second attempt |
| `backoff` | `2.0` | Multiplier applied to the delay on each subsequent attempt |
| `jitter` | `0.0` | Maximum fractional jitter added to each delay |

---

# Backoff Formula

The delay before attempt `n` (where `n = 1` is the second attempt):

```
delay = initial_delay_seconds × (backoff ^ n)
```

With defaults `initial_delay_seconds=1.0` and `backoff=2.0`:

| Attempt | Delay before it |
|---|---|
| 1st | none |
| 2nd | 1s |
| 3rd | 2s |
| 4th | 4s |

---

# Jitter

Jitter adds a random fractional increase to each computed delay, distributing retries to prevent thundering herd behavior when many orchestrations fail at the same time.

The actual delay becomes:

```
delay = delay × (1.0 + random(0, jitter))
```

With `jitter=0.2`, the delay is multiplied by a uniformly random value between 1.0 and 1.2.

Azure Durable Functions orchestrators must be deterministic — the same code must produce the same decisions on replay. Random values cannot be computed inside orchestrator code. The plugin therefore computes jitter inside a dedicated activity (`get_jitter_factor_activity`) and passes the result back to the orchestrator.

This activity is registered automatically as part of all executor registrations.

Setting `jitter=0.0` (the default) disables jitter entirely and skips the activity call.

---

# Applying a Retry Policy

Pass the policy to the executor constructor:

```python
from odyss_ai_flows_durable import DurableFunctionsExecutor, DurableRetryPolicy

executor = DurableFunctionsExecutor(
    client,
    retry_policy=DurableRetryPolicy(attempts=5, backoff=3.0),
)
```

The same constructor argument applies to `DurableSequenceExecutor` and `DurableParallelExecutor`.

---

# Scope of the Policy

**Single flow (`DurableFunctionsExecutor`)** — the policy applies per node activity. Each node retries independently up to `attempts` times before the overall flow fails. Nodes that already completed are not re-executed.

**Sequence (`DurableSequenceExecutor`)** — the policy applies per step. Each step retries up to `attempts` times before the sequence fails. Earlier steps that completed successfully are not re-run.

**Parallel (`DurableParallelExecutor`)** — the policy applies per step. All steps are dispatched together initially. On failure, only the failed steps are retried on subsequent attempts. Successful steps are not re-executed.

---

# DurableRetryPolicy vs. RetryOptions

`DurableRetryPolicy` is the plugin's own retry abstraction. It controls timing, backoff, and jitter, and is serialized into the orchestration payload so retries work correctly across replay.

`df.RetryOptions` is Azure Durable Functions' built-in retry mechanism. It is passed to `register()` and applies as the default fallback for sub-orchestrator calls when no `DurableRetryPolicy` is provided.

Both can coexist. When a `DurableRetryPolicy` is set, it governs node-level and step-level retries. `RetryOptions` governs the sub-orchestrator scheduling layer underneath.
