# Extension Points

The framework exposes multiple extension points intended for:
- plugins
- infrastructure integration
- execution customization
- orchestration specialization
- provider integration
- runtime augmentation

These extension points intentionally operate at different architectural layers.

This allows extensions to remain:
- lightweight
- composable
- explicit
- incremental

rather than requiring complete framework replacement.

---

# Design Philosophy

The framework intentionally avoids:
- monolithic provider abstractions
- opaque orchestration engines
- rigid plugin systems
- closed execution pipelines

Instead, individual subsystems expose focused extension points.

This allows users to:
- extend only what they need
- replace only specific behaviors
- keep defaults where appropriate

without rewriting the rest of the framework.

---

# Important Note

Most users should initially use:
- default matchers
- default handlers
- default pipelines
- default middleware
- default strategies

The extension system exists to support:
- advanced orchestration
- provider integrations
- infrastructure specialization
- execution experimentation

rather than to require customization for ordinary usage.

---

# Filesystem Matchers

The file subsystem supports custom repository matchers.

Registration:

```python
register_matcher(...)
```

Matchers define:
- how repository entries are recognized
- which files become semantic flow entities
- how repository files map into framework concepts

---

# What Matchers Control

Matchers determine:
- file type recognition
- node type discovery
- metadata file discovery
- repository semantics

Examples:
- `.jinja2`
- `.py`
- `.model.py`
- `outputs.json`

are all implemented through matchers.

---

# Typical Matcher Use Cases

Matchers are primarily intended for:
- new repository file types
- domain-specific orchestration formats
- custom metadata systems
- specialized execution semantics

This is considered an advanced extension point.

---

# Custom Node Types

The builder subsystem supports custom handlers through:

```python
register_handler(...)
```

This allows entirely new node execution types to be introduced.

---

# What Handlers Control

Handlers define:
- how nodes execute
- execution semantics
- orchestration behavior
- runtime interpretation

Examples:
- Python nodes
- Jinja/LLM nodes

are implemented through handlers.

---

# Typical Handler Use Cases

Custom handlers may implement:
- new provider systems
- multimodal execution
- workflow engines
- external runtimes
- orchestration adapters
- specialized execution semantics

This is one of the most powerful extension points in the framework.

It is also one of the most advanced.

---

# Configuration Providers

The config subsystem supports custom providers through:

```python
register_provider(...)
```

This is one of the most commonly used extension points.

---

# What Providers Control

Providers allow config values to resolve dynamically.

Examples:

```jinja2
{{ ENV("KEY") }}

{{ SECRET("db-password") }}

{{ CONFIG("shared.setting") }}
```

Providers participate directly in:
- config rendering
- config resolution
- runtime configuration semantics

---

# Typical Provider Use Cases

Providers commonly implement:
- secret systems
- external config stores
- environment integration
- cloud settings
- feature flags
- centralized configuration

This extension point is intentionally lightweight and easy to use.

---

# Runtime Strategies

The runtime/executor boundary supports custom execution strategies.

Strategies may be:
- passed directly to `run_flow()`
- or registered globally as defaults

---

# Global Default Strategy

Example:

```python
set_default_strategy_factory(
    lambda: LeasedConcurrencyStrategy(4)
)
```

This affects future flow executions automatically.

---

# Per-Flow Strategies

Example:

```python
await run_flow(
    "my_flow",
    strategy=MyCustomStrategy()
)
```

This affects only the current execution.

---

# What Strategies Control

Strategies define:
- concurrency behavior
- execution leasing
- scheduling semantics
- await policies
- runtime execution coordination

Examples:
- unlimited execution
- leased concurrency
- custom execution throttling

---

# Typical Strategy Use Cases

Strategies are useful for:
- resource limiting
- infrastructure throttling
- workload shaping
- execution fairness
- orchestration experimentation

---

# Composed Handler Pipelines

The composed handler system is one of the most important extension surfaces in the framework.

It exposes:
- pipeline registration
- component registration
- rendering augmentation
- provider callers
- multimodal execution
- action systems
- structured outputs

inside a unified execution architecture.

---

# Pipeline Components

Components may be registered dynamically.

Example:

```python
register_handler_component(
    "token_counter",
    TokenCounter
)
```

Components become reusable execution phases.

---

# Pipelines

Pipelines compose components declaratively.

Example:

```python
[
    "render",
    "messages_role",
    "call_azure",
    "token_counter",
]
```

Pipelines define:
- execution stages
- ordering
- augmentation behavior
- execution semantics

---

# What Pipelines Enable

Pipelines allow:
- provider integrations
- streaming execution
- structured outputs
- multimodal execution
- action systems
- execution instrumentation

without changing orchestration semantics.

---

# Why This Extension Point Is Crucial

The pipeline system is the primary mechanism through which:
- LLM behavior
- provider integration
- execution augmentation

remain:
- modular
- composable
- provider-independent

while preserving explicit orchestration semantics.

This is one of the most important architectural systems in the framework.

---

# Middleware

Middleware provides lightweight execution wrapping.

Registration:

```python
register_middleware(
    "logging",
    logging_middleware
)
```

Middleware works with all node types.

---

# What Middleware Controls

Middleware may:
- wrap execution
- short-circuit execution
- add retries
- add metrics
- enforce authorization
- add instrumentation
- modify runtime behavior

without changing handlers or pipelines.

---

# Middleware vs Pipelines

Pipelines primarily affect:
- internal LLM execution behavior

Middleware primarily affects:
- node execution behavior

The two systems are complementary rather than competing.

---

# Combined Power of the Extension System

These extension points intentionally operate at different architectural layers:

| Layer | Extension Point |
|---|---|
| Repository semantics | matchers |
| Node execution types | handlers |
| Config resolution | providers |
| Runtime scheduling | strategies |
| LLM execution behavior | pipelines/components |
| Node execution wrapping | middleware |

Together they create a highly composable architecture.

---

# Incremental Extensibility

One of the most important design goals is that extensions remain incremental.

Users may:
- keep defaults almost everywhere
- replace only one subsystem
- specialize only one execution layer

without redesigning the entire framework.

Example:
- custom provider
- default Azure pipeline
- default executor
- custom middleware

is entirely valid.

---

# Plugins vs Bootstrap Customization

Extension points may be used:
- directly during application bootstrap
- or exposed through reusable plugins

The framework intentionally supports both approaches.

---

# Future Evolution

The extension surface is expected to expand over time as:
- new providers
- new orchestration models
- new execution systems
- new multimodal capabilities

are introduced.

The current architecture is intentionally designed so these systems can evolve without forcing redesign of existing flows.

---

# Design Philosophy

The framework intentionally exposes:
- explicit
- focused
- composable

extension points instead of:
- giant inheritance hierarchies
- opaque provider systems
- centralized orchestration engines

This allows users to:
- extend deeply when necessary
- stay lightweight otherwise
- preserve explicit orchestration semantics
- avoid framework lock-in

while still supporting highly sophisticated execution architectures when required.