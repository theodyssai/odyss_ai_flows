# Middleware

The framework supports optional execution middleware for all node types.

Middleware provides a lightweight mechanism for:
- execution wrapping
- logging
- instrumentation
- retries
- metrics
- authorization
- execution policies
- short-circuiting
- behavioral augmentation

without modifying:
- node code
- handlers
- pipelines
- orchestration structure

Middleware is intentionally orthogonal to the pipeline system.

---

# Middleware vs Pipelines

Middleware and pipelines solve different problems.

---

## Pipelines

Pipelines define:
- how LLM nodes execute internally
- rendering stages
- provider calling
- structured parsing
- actions
- streaming
- multimodal behavior

Pipelines primarily affect:
- handler internals
- LLM execution semantics

---

## Middleware

Middleware wraps:
- node execution itself

independently of:
- node type
- handler implementation
- pipeline behavior

Middleware primarily affects:
- runtime execution behavior
- orchestration-level augmentation

---

# Middleware Applies to All Node Types

Middleware works with:
- Python nodes
- Jinja/LLM nodes
- structured nodes
- action-enabled nodes
- multimodal nodes
- streaming nodes

because middleware wraps the final handler execution layer rather than provider internals.

---

# The Core Idea

Middleware wraps execution using:

```python
middleware(call, handler)
```

and returns a wrapped async callable.

Example:

```python
def middleware_a(call, handler):

    async def wrapped(**kwargs):

        print("before")

        result = await call(**kwargs)

        print("after")

        return result

    return wrapped
```

---

# Middleware Registration

Middleware is registered globally.

Example:

```python
from odyss_ai_flows import *


register_middleware(
    "middleware_a",
    middleware_a,
)
```

The middleware may then be referenced in configuration.

---

# Applying Middleware

Middleware is attached through config:

```json
{
  "middleware": [
    "middleware_a"
  ]
}
```

This follows ordinary scoped configuration semantics.

Middleware may therefore be applied:
- globally
- per flow
- per folder
- per node
- through variants
- through runtime overrides

---

# Example: Node-Level Middleware

Example:

```text
flow/
├── node_a.py
└── node_a.config.json
```

`node_a.config.json`:

```json
{
  "middleware": [
    "middleware_a"
  ]
}
```

Only `node_a` receives the middleware.

---

# Example Middleware

```python
from odyss_ai_flows import *


def logging_middleware(call, handler):

    async def wrapped(**kwargs):

        print(
            f"Running: {handler.node.name}"
        )

        result = await call(**kwargs)

        print(
            f"Finished: {handler.node.name}"
        )

        return result

    return wrapped


register_middleware(
    "logging",
    logging_middleware,
)
```

---

# Middleware Ordering

Middleware order is deterministic.

Example config:

```json
{
  "middleware": [
    "middleware_a",
    "middleware_b"
  ]
}
```

Execution becomes:

```text
middleware_a(before)
    ↓
middleware_b(before)
    ↓
node execution
    ↓
middleware_b(after)
    ↓
middleware_a(after)
```

This behaves like ordinary nested wrapping.

---

# Example Ordering Trace

Example behavior:

```text
ordered_node:a_before
ordered_node:b_before
ordered_node:node
ordered_node:b_after
ordered_node:a_after
```

This demonstrates:
- deterministic nesting
- execution symmetry
- predictable wrapping behavior

:contentReference[oaicite:0]{index=0}

---

# Middleware Isolation

Middleware only affects the node where it is applied.

This is extremely important.

Middleware does not automatically propagate:
- through `nget()`
- through dependencies
- through nested execution

Each node resolves its own middleware independently.

---

# Example Isolation

Example:

```text
node_a
    middleware_a

node_b
    middleware_b
```

Even if:

```python
await nget(node_a)
```

inside `node_b`,
the middleware remains isolated.

Result:

```text
node_a → middleware_a only
node_b → middleware_b only
```

:contentReference[oaicite:1]{index=1}

---

# Middleware Does Not Affect Dependencies

Middleware wraps:
- execution behavior

not:
- dependency graph construction
- orchestration semantics
- `nget()` behavior

The execution graph remains unchanged.

---

# Middleware and Eager Execution

All nodes still begin execution eagerly as normal.

Middleware does not change:
- orchestration startup semantics
- dependency resolution semantics
- lazy node semantics

Middleware only wraps node execution once execution begins.

---

# Short-Circuit Middleware

Middleware may bypass node execution entirely.

Example:

```python
def short_circuit_middleware(
    call,
    handler,
):

    async def wrapped(**kwargs):

        return {
            "blocked": True
        }

    return wrapped
```

In this case:
- node code never executes
- middleware returns immediately
- orchestration continues normally

---

# Example: Authorization Middleware

```python
def auth_middleware(call, handler):

    async def wrapped(**kwargs):

        user = await iget("user")

        if not user.is_admin:

            return {
                "error": "access denied"
            }

        return await call(**kwargs)

    return wrapped
```

This allows execution policies to remain external to node logic.

---

# Middleware Exceptions

Middleware exceptions behave like ordinary node failures.

Example:

```python
raise RuntimeError(
    "middleware failure"
)
```

Results in:
- node failure
- normal flow error propagation
- ordinary orchestration semantics

Middleware does not introduce separate error behavior.

:contentReference[oaicite:2]{index=2}

---

# Middleware and Logging

Middleware is especially useful for:
- execution tracing
- instrumentation
- metrics
- profiling
- debugging

because it wraps the actual execution layer.

Example:

```python
import time


def timing_middleware(call, handler):

    async def wrapped(**kwargs):

        start = time.time()

        result = await call(**kwargs)

        duration = (
            time.time() - start
        )

        logger.info(
            f"{handler.node.name} "
            f"took {duration}s"
        )

        return result

    return wrapped
```

---

# Middleware and Retry Logic

Middleware may also implement:
- retry policies
- fallback behavior
- transient failure handling

Example:

```python
def retry_middleware(call, handler):

    async def wrapped(**kwargs):

        for _ in range(3):

            try:
                return await call(**kwargs)

            except Exception:
                pass

        raise RuntimeError(
            "retry limit exceeded"
        )

    return wrapped
```

---

# Middleware and LLM Nodes

Middleware works naturally with LLM nodes.

Example:
- timing generation
- logging prompts
- enforcing execution policies
- usage monitoring
- custom authorization

without modifying:
- pipelines
- providers
- caller components

---

# Middleware and Python Nodes

Middleware also works naturally with ordinary Python nodes.

Example:
- tracing
- profiling
- permission checks
- caching
- instrumentation

This creates a unified augmentation system across all execution types.

---

# Middleware and Nested Flows

Middleware remains local to each flow execution repository.

Nested flows resolve middleware independently according to:
- their own config scopes
- their own variants
- their own runtime overrides

This preserves flow isolation semantics.

---

# Middleware and Pipelines Together

Middleware and pipelines compose naturally.

Example execution:

```text
middleware
    ↓
handler execution
    ↓
LLM pipeline
    ↓
provider execution
```

Middleware wraps the node execution layer while pipelines manage internal LLM execution semantics.

---

# Design Philosophy

Middleware intentionally remains:
- lightweight
- execution-oriented
- orchestration-agnostic

It is not intended to replace:
- pipelines
- handlers
- orchestration semantics

Instead, middleware provides a clean way to augment node execution behavior externally.

This keeps:
- node logic clean
- orchestration explicit
- execution augmentation modular
- runtime behavior composable

without introducing hidden orchestration systems or provider-specific coupling.