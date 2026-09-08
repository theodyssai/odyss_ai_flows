# Pre-Resolved Config Trees

By default, configuration values are resolved lazily.

This means semantic providers, references, and runtime config expressions are only resolved when values are actually requested through `cget()`.

For most flows, this is the preferred behavior.

However, the framework also supports pre-resolving configuration trees into fully operational runtime representations before execution begins.

This is called pre-resolution.

---

# Lazy vs Pre-Resolved Configuration

Normal lazy behavior:

```python
value = await cget("azure_openai.api_key")
```

Resolution happens:
- at runtime
- on demand
- only when requested

Pre-resolved behavior:

```python
await pre_resolve_config_tree_async()
```

Resolution happens:
- eagerly
- before runtime access
- across the entire config tree

The resolved values are then stored directly inside the flow-local runtime config tree.

---

# What Pre-Resolution Actually Does

Pre-resolution performs several operations:
- semantic Jinja rendering
- provider execution
- `REF()` traversal
- recursive config resolution
- runtime operationalization
- semantic cache warming

The resulting config tree becomes a fully resolved operational runtime structure optimized for repeated access.

---

# Why Pre-Resolution Exists

Pre-resolution is primarily useful for:
- reducing repeated runtime resolution overhead
- validating configuration early
- surfacing provider failures before execution
- operationalizing large config trees
- reducing runtime semantic rendering cost
- long-running orchestration systems
- repeated `cget()` access patterns

Most small flows do not require it.

---

# Enabling Pre-Resolution

Pre-resolution can be enabled directly through `run_flow()`.

Example:

```python
from odyss_ai_flows import run_flow
import asyncio


async def main():

    result = await run_flow(
        "article_flow",
        pre_resolve_config=True
    )

    print(result)


asyncio.run(main())
```

This pre-resolves the entire flow-local config tree before execution starts.

---

# Flow-Local Pre-Resolution

Flow-local pre-resolution mutates the active runtime config tree into a resolved operational representation.

This means semantic expressions are replaced by their resolved values directly inside the runtime config tree.

Example:

Before pre-resolution:

```json
{
  "api_key": "{{ VAULT('openai-key') }}"
}
```

After pre-resolution:

```json
{
  "api_key": "<resolved sensitive value>"
}
```

Subsequent `cget()` calls retrieve the already-resolved value directly.

---

# `REF()` Traversal During Pre-Resolution

Pre-resolution also resolves `REF()` graph traversal eagerly.

Example:

```json
{
  "default_model": "gpt-4o",

  "active_model": "{{ REF('default_model') }}"
}
```

After pre-resolution:

```json
{
  "default_model": "gpt-4o",

  "active_model": "gpt-4o"
}
```

This removes additional runtime reference traversal overhead during later config access.

---

# Semantic Cache Warming

Pre-resolution automatically warms the semantic config cache.

This reduces repeated:
- provider execution
- semantic rendering
- Jinja evaluation

during runtime access.

This can become useful in:
- large orchestration systems
- provider-heavy config structures
- long-running workflows
- deeply nested flows

---

# Global Config Pre-Resolution

The framework also supports pre-resolving global configuration separately.

Unlike flow-local pre-resolution, global pre-resolution does not mutate the global config storage itself.

Instead, it primarily:
- resolves semantic expressions
- warms semantic caches
- validates provider behavior

This allows global semantic configuration to become operationally warm before flow execution begins.

---

# Example: Lazy Resolution

Example config:

```json
{
  "api_key": "{{ VAULT('openai-key') }}"
}
```

Without pre-resolution:

```python
value = await cget("api_key")
```

The provider executes at access time.

---

# Example: Pre-Resolved Execution

With:

```python
await run_flow(
    "article_flow",
    pre_resolve_config=True
)
```

The provider executes during initialization instead.

Later runtime reads retrieve the already-resolved operational value.

---

# Relationship to Scoped Configuration

Pre-resolution fully respects:
- config scoping
- folder inheritance
- node-specific config
- merge semantics
- runtime overrides
- semantic providers

The entire effective runtime config tree is resolved after all scope merging completes.

---

# Runtime Overrides and Pre-Resolution

Runtime overrides continue to work normally after pre-resolution.

Example:

```python
config.override(
    scope="",
    key="generation.temperature",
    value=0.1
)
```

The override becomes part of the runtime config tree immediately.

Newly introduced semantic expressions may still resolve lazily through `cget()` unless explicitly pre-resolved again.

---

# Nested Flows

Nested flows maintain independent config trees.

This means:
- pre-resolution state is flow-local
- nested flows may choose different resolution modes
- runtime config operationalization remains isolated

Pre-resolving one flow does not automatically pre-resolve unrelated nested flows.

---

# Operational Tradeoffs

Lazy resolution provides:
- lower startup overhead
- deferred provider execution
- minimal unused work

Pre-resolution provides:
- earlier validation
- reduced runtime semantic overhead
- operationalized config trees
- warm semantic caches

The framework supports both approaches because different orchestration systems benefit from different execution characteristics.

---

# Typical Usage

Most simple flows should continue using default lazy resolution.

Pre-resolution becomes more useful in systems with:
- large config trees
- many semantic providers
- repeated config access
- long-running orchestration
- external secret systems
- provider-heavy execution
- large nested orchestration structures

---

# Design Philosophy

The framework intentionally separates:
- config structure building
- semantic resolution
- runtime execution

This allows configuration systems to remain:
- composable
- lazy by default
- operationally optimizable
- runtime-aware
- execution-local

without forcing a single configuration execution strategy on every flow.

Pre-resolution is therefore treated as an optional runtime optimization and operationalization mechanism rather than mandatory framework behavior.