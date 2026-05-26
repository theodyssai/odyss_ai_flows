# Configuration and `cget()`

The framework includes a hierarchical scoped configuration system designed specifically for flow-based orchestration.

Configuration is intentionally:
- layered
- local
- composable
- runtime-aware
- execution-scoped

rather than centralized into a single global settings file.

The goal is allowing small flows to remain simple while enabling large systems to evolve without configuration chaos.

---

# Configuration Philosophy

The framework intentionally separates three different concepts:

| Purpose | API |
|---|---|
| Runtime inputs | `iget()` |
| Node dependencies | `nget()` |
| Scoped configuration | `cget()` |

These systems serve different purposes:
- `iget()` provides external runtime values
- `nget()` synchronizes with node execution
- `cget()` provides hierarchical configuration

This separation keeps orchestration logic easier to reason about as systems grow.

---

# Global Configuration

Global configuration is stored in:

```text
global_config.json
```

located at the execution root.

Example:

```json
{
  "azure_openai": {
    "deployment_name": "gpt-4o",
    "temperature": 0.7
  }
}
```

Global configuration is accessible:
- inside flows
- inside nodes
- outside flow execution entirely

Example:

```python
from odyss_ai_flows import cget
import asyncio


async def main():

    deployment = await cget(
        "azure_openai.deployment_name"
    )

    print(deployment)


asyncio.run(main())
```

When used outside active node execution, `cget()` resolves values directly from global configuration.

---

# Scoped Configuration

Inside node execution, configuration becomes scope-aware.

This means configuration values are resolved dynamically based on the currently executing node location.

Configuration is inherited progressively through folder hierarchy.

More local configuration overrides broader configuration.

---

# Folder Configuration

Folder-level configuration uses:

```text
config.json
```

Example structure:

```text
global_config.json

article_flow/
├── config.json
├── summarization/
│   ├── config.json
│   ├── summarize.jinja2
│   └── cleanup.py
│
└── classification/
    └── classify.jinja2
```

In this structure:
- `global_config.json` applies globally
- `article_flow/config.json` applies to the entire flow
- `summarization/config.json` applies only to nodes inside `summarization`

Configuration becomes progressively more specific as execution scope becomes more local.

---

# Node-Specific Configuration

Individual nodes may also define dedicated configuration files.

Format:

```text
<node_name>.config.json
```

Example:

```text
summarize.jinja2
summarize.config.json
```

This creates node-local configuration overrides.

Node-specific config is the most specific configuration layer and overrides broader folder configuration when applicable.

---

# Configuration Resolution Order

Configuration is resolved progressively from broader scopes to narrower scopes.

Conceptually:

```text
global_config.json
    ↓
flow_root/config.json
    ↓
nested_folder/config.json
    ↓
<node_name>.config.json
```

Each layer contributes configuration values to the final effective runtime configuration.

---

# Using `cget()`

Configuration values are accessed through `cget()`.

Example:

```python
temperature = await cget(
    "azure_openai.temperature"
)
```

`cget()` is asynchronous because configuration values may require:
- runtime resolution
- provider execution
- semantic rendering
- dynamic reference traversal

even though simple values often behave like ordinary configuration lookups.

---

# Dotted Access

Configuration keys use dotted traversal syntax.

Example:

```python
await cget("azure_openai.temperature")
```

instead of:

```python
config["azure_openai"]["temperature"]
```

This keeps configuration access compact and readable inside orchestration logic.

---

# Using `cget()` in Python Nodes

Example:

```python
from odyss_ai_flows import *


@node
async def summarize():

    deployment = await cget(
        "azure_openai.deployment_name"
    )

    temperature = await cget(
        "azure_openai.temperature",
        default=0.7
    )

    article = await nget("article")

    return f"""
Deployment: {deployment}

Temperature: {temperature}

Article:
{article}
"""
```

---

# Using `cget()` in Jinja Nodes

`cget()` is automatically available inside Jinja templates.

Example:

```jinja2
Deployment:

{{ cget("azure_openai.deployment_name") }}

Temperature:

{{ cget("azure_openai.temperature", default=0.7) }}
```

Like `nget()`, awaiting is handled automatically inside Jinja execution.

---

# Defaults

`cget()` supports default values.

Example:

```python
timeout = await cget(
    "timeouts.request",
    default=30
)
```

If the key does not exist, the default value is returned instead.

This allows sparse configuration without requiring every value to exist globally.

---

# Merge Semantics

Configuration merging behaves differently depending on value type.

This is one of the most important behaviors of the configuration system.

---

# Dictionary Merge Behavior

Dictionaries merge progressively across scopes.

Example:

Global configuration:

```json
{
  "azure_openai": {
    "deployment_name": "gpt-4o",
    "temperature": 0.7,
    "max_tokens": 1000
  }
}
```

Nested folder config:

```json
{
  "azure_openai": {
    "temperature": 0.2
  }
}
```

Effective runtime result:

```json
{
  "deployment_name": "gpt-4o",
  "temperature": 0.2,
  "max_tokens": 1000
}
```

Only overridden fields change while the rest of the structure remains inherited.

---

# Scalar Override Behavior

Non-dictionary values overwrite completely.

Example:

Global configuration:

```json
{
  "provider": "gpt4"
}
```

Nested config:

```json
{
  "provider": "claude"
}
```

Effective result:

```json
"claude"
```

This creates intuitive shadowing behavior for scalar values while preserving structural merging for dictionaries.

---

# Practical Example

Example structure:

```text
global_config.json

article_flow/
├── config.json
├── summarize.jinja2
├── summarize.config.json
└── cleanup.py
```

`global_config.json`:

```json
{
  "azure_openai": {
    "deployment_name": "gpt-4o",
    "temperature": 0.7,
    "max_tokens": 1000
  }
}
```

`article_flow/config.json`:

```json
{
  "azure_openai": {
    "temperature": 0.4
  }
}
```

`summarize.config.json`:

```json
{
  "azure_openai": {
    "max_tokens": 300
  }
}
```

Inside `summarize.jinja2`:

```python
await cget("azure_openai")
```

effectively resolves to:

```json
{
  "deployment_name": "gpt-4o",
  "temperature": 0.4,
  "max_tokens": 300
}
```

This demonstrates:
- global inheritance
- folder overrides
- node-local overrides
- dictionary merging

working together simultaneously.

---

# Lazy Resolution and Caching

Configuration values are resolved lazily.

This means values are only processed when actually requested through `cget()`.

Resolved semantic templates are also cached automatically to reduce repeated processing overhead during runtime execution.

In practice, this allows the configuration system to remain:
- flexible
- dynamic
- runtime-aware

without introducing excessive runtime overhead for ordinary flows.

---

# Configuration Scope and Isolation

Configuration is scoped per flow run.

This means:
- concurrent flows do not share runtime config state
- nested flows receive independent config trees
- runtime modifications remain isolated
- orchestration stays predictable

This becomes especially important once systems begin using:
- nested flows
- reusable orchestration modules
- concurrent execution
- long-running workflows

where global mutable configuration would quickly become problematic.

---

# Optional Configuration

All configuration layers are optional.

Small flows may use only:

```text
global_config.json
```

while larger systems may use extensive scoped configuration hierarchies.

The framework intentionally supports gradual scaling from:
- minimal experimentation

to:

- large modular orchestration systems

without changing the underlying configuration model.