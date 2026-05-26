# Runtime Config Overrides

The framework allows configuration values to be modified dynamically during flow execution.

These modifications are called runtime config overrides.

Runtime overrides make it possible to:
- alter execution behavior dynamically
- specialize nested orchestration
- inject temporary execution parameters
- modify provider behavior
- adjust runtime tuning
- influence downstream nodes and subflows

without modifying filesystem configuration files.

---

# Runtime Overrides Are Flow-Local

Runtime overrides modify the active flow-local configuration tree.

They do not modify:
- `global_config.json`
- filesystem config files
- process-global state
- unrelated flow executions

Overrides are isolated to the currently executing flow runtime.

This means:
- concurrent executions remain independent
- nested flows remain isolated
- runtime orchestration stays predictable

even when many flows execute simultaneously.

---

# Relationship to Scoped Configuration

Runtime overrides fully participate in the normal scoped configuration system.

This means overrides:
- respect node scopes
- follow merge semantics
- participate in dotted traversal
- behave like ordinary config layers

rather than acting as a separate override mechanism.

---

# Basic Override Example

Example:

```python
from odyss_ai_flows import *


@node
async def configure():

    config.override(
        scope="",
        key="azure_openai.temperature",
        value=0.2
    )

    return "Configured"
```

This modifies the active runtime config tree for the current flow execution.

Subsequent `cget()` calls will resolve the overridden value.

---

# Root Scope Overrides

Using:

```python
scope=""
```

targets the root flow configuration scope.

This behaves similarly to overriding values at the broadest flow-local level.

Example:

```python
config.override(
    scope="",
    key="timeouts.request",
    value=60
)
```

---

# Scoped Overrides

Overrides can also target specific flow scopes.

Example:

```python
config.override(
    scope="summarization",
    key="azure_openai.temperature",
    value=0.1
)
```

This override only affects nodes executing inside:

```text
summarization/
```

scope.

---

# Node-Level Overrides

Overrides may target deeply specific execution scopes.

Example:

```python
config.override(
    scope="summarization/rewrite",
    key="azure_openai.max_tokens",
    value=300
)
```

This creates highly localized runtime behavior adjustments without affecting unrelated parts of the flow.

---

# Overrides Participate in Merge Semantics

Overrides behave exactly like normal config entries.

Dictionary values merge progressively.

Example:

Existing config:

```json
{
  "azure_openai": {
    "deployment_name": "gpt-4o",
    "temperature": 0.7,
    "max_tokens": 1000
  }
}
```

Runtime override:

```python
config.override(
    scope="",
    key="azure_openai.temperature",
    value=0.2
)
```

Effective runtime config:

```json
{
  "deployment_name": "gpt-4o",
  "temperature": 0.2,
  "max_tokens": 1000
}
```

Only the overridden field changes.

---

# Missing Paths Are Created Automatically

Overrides automatically create missing intermediate paths.

Example:

```python
config.override(
    scope="",
    key="custom.settings.debug_mode",
    value=True
)
```

This creates the missing structure automatically inside the runtime config tree.

---

# Runtime Overrides and `cget()`

Overrides become immediately visible through `cget()`.

Example:

```python
from odyss_ai_flows import *


@node
async def configure():

    config.override(
        scope="",
        key="generation.temperature",
        value=0.1
    )

    value = await cget(
        "generation.temperature"
    )

    return value
```

Result:

```python
0.1
```

---

# Dynamic Runtime Behavior

Runtime overrides are especially useful for:
- orchestration tuning
- adaptive execution
- nested flow specialization
- temporary provider switching
- experimental execution logic
- dynamic LLM behavior
- runtime policy adjustment

Example:

```python
from odyss_ai_flows import *


@node
async def route_generation():

    complexity = await nget(
        "complexity_analysis"
    )

    if complexity == "high":

        config.override(
            scope="generation",
            key="azure_openai.temperature",
            value=0.1
        )

    else:

        config.override(
            scope="generation",
            key="azure_openai.temperature",
            value=0.8
        )

    return "Configured"
```

This allows orchestration behavior to adapt dynamically during runtime execution.

---

# Runtime Overrides Inside Nested Flows

Nested flows receive independent configuration trees.

This means runtime overrides inside one flow do not automatically leak into unrelated nested flows.

Overrides remain isolated to the active flow execution context unless explicitly propagated through orchestration logic.

This preserves predictable modular composition even in deeply nested systems.

---

# Runtime Overrides vs Inputs

Runtime overrides differ from `iget()` inputs.

| Mechanism | Purpose |
|---|---|
| `iget()` | runtime business data |
| `cget()` | configuration |
| `config.override()` | dynamic runtime configuration mutation |

This distinction helps preserve clean orchestration architecture as systems grow.

---

# Runtime Overrides vs Filesystem Config

Overrides are temporary runtime behavior.

They do not modify:
- config files
- repositories
- source-controlled configuration
- persisted runtime state

The override exists only for the lifetime of the active flow execution.

Once execution ends, the override disappears automatically.

---

# Runtime Overrides and Semantic Providers

Overrides can contain:
- ordinary literals
- semantic provider expressions
- references
- dynamic config structures

Example:

```python
config.override(
    scope="",
    key="api_key",
    value="{{ ENV('TEMP_API_KEY') }}"
)
```

The value continues to participate in normal semantic config resolution behavior through `cget()`.

---

# Design Philosophy

Runtime overrides intentionally allow orchestration systems to modify configuration behavior dynamically while preserving:
- scoped semantics
- execution isolation
- predictable inheritance
- flow-local state
- async-safe execution

The goal is enabling dynamic orchestration behavior without introducing:
- global mutable state
- hidden runtime mutation
- process-wide configuration leakage
- orchestration unpredictability

This becomes increasingly important in systems using:
- nested flows
- reusable orchestration modules
- adaptive AI execution
- dynamic provider routing
- concurrent runtime execution
- long-running orchestration systems