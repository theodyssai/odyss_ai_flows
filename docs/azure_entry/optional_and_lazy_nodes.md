# Lazy Nodes and Skipping

The framework uses an eager execution model.

By default:
- all nodes begin execution immediately
- nodes run concurrently
- execution pauses only when waiting for dependencies through `nget()`

This behavior is one of the core orchestration principles of the framework.

At the same time, the framework also supports:
- demand-driven execution
- optional orchestration branches
- conditional LLM execution
- execution skipping

through a combination of:
- lazy nodes
- ordinary Python control flow
- Jinja `skip()` semantics

---

# Eager Execution Model

When a flow starts:
- all non-lazy nodes are scheduled immediately
- execution proceeds concurrently
- nodes pause only when blocked on unresolved dependencies

Example:

```text
color.jinja2
fruit.jinja2
description.jinja2
```

Execution conceptually behaves like:

```text
all nodes start
    ↓
fruit waits for nget("color")
    ↓
description waits for nget("fruit")
    ↓
dependencies resolve dynamically
```

This differs from orchestration systems that:
- statically topologically sort entire graphs
- execute nodes one-by-one
- schedule execution only after dependency analysis

The framework instead treats flows as:
- async execution systems
- with dynamic synchronization points

---

# Dependency Pausing with `nget()`

`nget()` is the synchronization mechanism between nodes.

Example:

```python
from odyss_ai_flows import *


@node
async def description():

    fruit = await nget("fruit")

    return f"""
Describe this fruit:

{fruit}
"""
```

If `fruit` has not completed yet:
- execution pauses
- other nodes continue progressing
- orchestration remains fully async

---

# Lazy Nodes

Lazy nodes behave differently.

A lazy node does not begin execution automatically.

Instead:
- it remains dormant
- it only activates if referenced through `nget()`

This creates demand-driven orchestration behavior.

---

# Configuring Lazy Nodes

Lazy behavior is controlled through scoped configuration.

Example:

```json
{
  "execution": {
    "lazy": true
  }
}
```

This may be applied:
- globally
- per folder scope
- per node
- through variants
- through runtime overrides

like any other configuration value.

---

# Example: Lazy Node

Example structure:

```text
article_flow/
├── summarize.jinja2
├── expensive_analysis.jinja2
└── route.py
```

`expensive_analysis.config.json`:

```json
{
  "execution": {
    "lazy": true
  }
}
```

`route.py`:

```python
from odyss_ai_flows import *


@node
async def route():

    should_analyze = await nget(
        "decision"
    )

    if should_analyze:

        return await nget(
            "expensive_analysis"
        )

    return "Skipped analysis"
```

In this scenario:
- `expensive_analysis` never begins execution unless explicitly requested
- unnecessary orchestration work is avoided
- unnecessary LLM calls are avoided

---

# Lazy Nodes Still Exist in the Flow

Lazy nodes still:
- exist in the repository
- exist in flow structure
- participate in dependency resolution
- have scopes and config
- can be referenced normally

They are simply execution-dormant until requested.

---

# Demand-Driven Execution

Lazy nodes combined with `nget()` create demand-driven orchestration behavior.

This allows flows to:
- activate expensive branches conditionally
- avoid unnecessary LLM calls
- reduce orchestration overhead
- reduce latency
- reduce API cost

without introducing:
- explicit conditional DAG syntax
- orchestration branching DSLs
- specialized conditional node types

---

# Python Nodes and No-Op Behavior

Python nodes do not support framework-level skipping semantics.

This is intentional.

Python nodes are treated as:
- arbitrary user code
- unrestricted execution logic
- fully general orchestration components

The framework therefore does not attempt to infer whether a Python node was "skipped."

Instead, ordinary Python control flow should be used.

Example:

```python
from odyss_ai_flows import *


@node
async def optional_cleanup():

    enabled = await iget(
        "cleanup_enabled",
        default=False
    )

    if not enabled:
        return None

    return "Cleanup complete"
```

Other common no-op patterns include:

```python
return ""
```

or:

```python
return None
```

or:

```python
if not condition:
    return
```

This preserves the framework philosophy that Python nodes remain unrestricted code rather than framework-managed orchestration templates.

---

# Jinja Nodes and `skip()`

Jinja nodes support a dedicated helper:

```python
skip()
```

`skip()` behaves differently from ordinary conditional rendering.

If `skip()` is triggered during Jinja processing:
- prompt generation stops
- the LLM call is never executed
- the node returns an empty string explicitly

This is useful when:
- the prompt should not be generated
- the LLM invocation would be unnecessary
- orchestration conditions invalidate the node
- optional prompt execution is desired

---

# Example: `skip()`

Example:

```jinja2
{% if not iget("enable_summary", False) %}

    {{ skip() }}

{% endif %}

Summarize this article:

{{ nget("article") }}
```

If:
```python
enable_summary=False
```

then:
- template processing aborts
- the LLM is never called
- the node returns `""`

---

# Why `skip()` Exists

Jinja nodes are fundamentally different from Python nodes.

Jinja nodes typically represent:
- prompt-producing nodes
- LLM execution requests
- expensive external calls

Avoiding the actual LLM invocation is therefore operationally meaningful.

`skip()` exists specifically to avoid:
- unnecessary prompt rendering
- unnecessary LLM execution
- unnecessary token usage
- unnecessary latency

while preserving normal orchestration structure.

---

# Difference Between Lazy, No-Op and Skip

These concepts solve different orchestration problems.

| Concept | Behavior |
|---|---|
| Lazy node | node never starts unless requested |
| Python no-op | node executes but returns inert result |
| Jinja `skip()` | node aborts before LLM call |

This distinction is important.

---

# Example Comparison

## Lazy node

```json
{
  "execution": {
    "lazy": true
  }
}
```

Node execution never begins unless referenced.

---

## Python no-op

```python
if not enabled:
    return None
```

Node executes normally but performs no meaningful work.

---

## Jinja skip

```jinja2
{{ skip() }}
```

Node aborts before LLM invocation entirely.

---

# Combining Lazy Nodes and Skip

These mechanisms may also work together.

Example:
- a node may be lazy
- and still use `skip()` internally after activation

This allows orchestration to remain:
- highly dynamic
- demand-driven
- resource-efficient

without requiring complex orchestration branching systems.

---

# Practical Use Cases

Typical usage includes:
- optional expensive analysis
- conditional summarization
- adaptive orchestration
- feature-gated execution
- user-selected processing
- API cost reduction
- latency optimization
- conditional nested flows

---

# Design Philosophy

The framework intentionally combines:
- eager orchestration
- async execution
- dependency synchronization
- demand-driven activation
- conditional prompt execution

inside a single execution model.

The goal is allowing orchestration systems to remain:
- dynamic
- composable
- async-native
- operationally efficient

without introducing:
- static DAG rigidity
- orchestration branching DSLs
- heavyweight conditional execution systems
- hidden scheduler behavior

The resulting model stays explicit while still supporting highly dynamic orchestration behavior.