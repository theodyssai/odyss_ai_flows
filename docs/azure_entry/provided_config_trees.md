# Provided Config Trees

The framework allows configuration trees to be supplied programmatically at runtime instead of being loaded from filesystem config files.

This is called a provided config tree.

Provided config trees allow:
- fully dynamic configuration generation
- external orchestration systems
- runtime-generated config structures
- testing environments
- synthetic execution contexts
- programmatic orchestration setup

without requiring physical config files on disk.

---

# Providing a Config Tree

A config tree can be supplied directly through `run_flow()`.

Example:

```python
from odyss_ai_flows import run_flow
import asyncio


async def main():

    result = await run_flow(
        "article_flow",

        provided_tree={
            "azure_openai": {
                "deployment_name": "gpt-4o",
                "temperature": 0.2
            }
        }
    )

    print(result)


asyncio.run(main())
```

The provided tree becomes the active runtime configuration tree for that flow execution.

---

# Relationship to Prepared Flows

Provided config trees may also be attached through prepared flow execution mechanisms.

This allows flows to be:
- pre-built
- pre-configured
- operationalized ahead of execution

while still remaining runtime-configurable.

Prepared flows are covered separately in dedicated documentation.

---

# Replacing Filesystem Config

When a provided config tree is supplied, filesystem-based scoped config loading is currently bypassed for the flow.

This means:
- `config.json` files are ignored
- `<node_name>.config.json` files are ignored
- flow folder config scanning is skipped

The provided tree becomes the primary runtime configuration source.

---

# Important Current Behavior

The current implementation intentionally replaces flow-local filesystem config behavior rather than merging with it.

Example:

```python
await run_flow(
    "article_flow",
    provided_tree={...}
)
```

does not merge with:

```text
flow_root/config.json
```

or:

```text
summarize.config.json
```

Those files are ignored entirely for that flow execution.

---

# Global Configuration Still Exists

`global_config.json` still remains available outside the flow-local tree system.

This means globally accessible configuration may still exist independently from the provided runtime tree.

However, the flow-local scoped config hierarchy itself is replaced by the provided tree.

---

# Provided Trees Still Support Scoping

Provided trees are not treated as flat dictionaries.

They still participate in:
- scoped config traversal
- dotted lookup
- merge semantics
- semantic provider resolution
- runtime overrides
- `cget()` access

exactly like ordinary filesystem-built config trees.

Example:

```python
value = await cget(
    "azure_openai.temperature"
)
```

works identically regardless of whether the config tree originated from:
- filesystem config files
- a provided runtime tree

---

# Semantic Providers Continue to Work

Provided trees fully support semantic providers.

Example:

```python
provided_tree={
    "azure_openai": {
        "api_key": "{{ SECRET('openai-key') }}"
    }
}
```

Provider semantics continue to function normally through `cget()` resolution.

This includes:
- `ENV()`
- `SECRET()`
- `CONFIG()`
- `REF()`
- `LITERAL_SECRET()`

and other registered providers.

---

# Runtime Overrides Continue to Work

Runtime config overrides also continue to function normally with provided trees.

Example:

```python
config.override(
    scope="",
    key="azure_openai.temperature",
    value=0.1
)
```

The override mutates the active runtime config tree regardless of how that tree was originally created.

---

# Example: Fully Programmatic Configuration

Example:

```python
from odyss_ai_flows import *
import asyncio


async def main():

    runtime_config = {
        "azure_openai": {
            "deployment_name": "gpt-4o",
            "temperature": 0.3,
            "api_key": "{{ ENV('OPENAI_API_KEY') }}"
        },

        "generation": {
            "style": "scientific"
        }
    }

    result = await run_flow(
        "article_flow",
        provided_tree=runtime_config,
        topic="black holes"
    )

    print(result)


asyncio.run(main())
```

This execution requires no flow-local filesystem configuration files.

---

# Why Provided Trees Exist

Provided config trees are primarily intended for:
- orchestration frameworks
- generated execution environments
- dynamic runtime systems
- external control planes
- testing infrastructure
- programmatic flow composition
- higher-level orchestration systems

where filesystem configuration may be:
- inconvenient
- insufficiently dynamic
- externally generated
- runtime-specific

---

# Interaction with Pre-Resolution

Provided trees fully support:
- lazy resolution
- pre-resolved execution
- semantic caching
- provider traversal

Example:

```python
await run_flow(
    "article_flow",
    provided_tree=my_tree,
    pre_resolve_config=True
)
```

This operationalizes the provided runtime config tree before execution begins.

---

# Nested Flows

Nested flows remain independent execution contexts.

A nested flow does not automatically inherit the provided tree of its parent flow unless explicitly passed through orchestration logic.

This preserves:
- execution isolation
- predictable composition
- reusable subflows
- independent runtime configuration

even in deeply nested systems.

---

# Current Limitations

The current implementation intentionally treats provided trees as a full replacement for flow-local filesystem configuration.

This means:
- no merging with folder configs
- no merging with node configs
- no hybrid filesystem/runtime scoped tree construction

Future versions may expand hybrid behavior, but current semantics are intentionally explicit and predictable.

---

# Design Philosophy

Provided config trees allow the configuration system to operate as:
- runtime-native
- programmatically composable
- orchestration-aware
- execution-local

rather than being strictly tied to filesystem structure.

At the same time, the framework intentionally preserves:
- explicit execution semantics
- scoped config behavior
- provider support
- runtime isolation
- deterministic orchestration behavior

regardless of whether configuration originates from:
- physical config files
- generated runtime structures
- external orchestration systems
- prepared execution environments