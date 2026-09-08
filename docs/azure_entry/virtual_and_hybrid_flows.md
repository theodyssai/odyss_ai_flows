# Virtual and Hybrid Flows

The framework supports virtual and hybrid flows through repository-level runtime composition.

This allows flows to be:
- partially generated at runtime
- fully generated at runtime
- extended dynamically
- assembled from reusable components
- composed from multiple sources

without bypassing the normal:
- repository system
- builder
- executor
- handler pipeline
- orchestration semantics

The framework therefore treats flows as repository compositions rather than strictly physical filesystem folders.

---

# What Is a Virtual Flow?

A virtual flow is a flow constructed partially or entirely through runtime repository injection rather than physical files.

Example:

```python
from odyss_ai_flows import *
import asyncio


async def main():

    flow = PreparedFlow()

    flow.fset(

        "summarize.jinja2",

        """
Summarize this article:

{{ iget("article") }}
"""
    )

    result = await run_flow(
        flow,
        article="Black holes are..."
    )

    print(result)


asyncio.run(main())
```

No physical flow files are required.

---

# What Is a Hybrid Flow?

A hybrid flow combines:
- physical filesystem flow files
- runtime-generated virtual repository entries

inside the same execution repository.

Example:

Filesystem flow:

```text
article_flow/
├── summarize.jinja2
└── classify.jinja2
```

Runtime augmentation:

```python
flow = PreparedFlow(
)

flow.fset(
    "analysis.py", type=python_node,
    analysis_callable
)
```

run_flow(flow)

The resulting runtime flow contains:
- physical nodes
- virtual nodes
- unified orchestration semantics

inside a single repository.

---

# `PreparedFlow`

Virtual and hybrid flows are created through:

```python
PreparedFlow
```

`PreparedFlow` does not:
- define orchestration separately
- bypass the builder
- bypass execution
- create alternate runtime semantics

Instead, it only records deferred repository mutations that are applied before normal flow execution begins.

This is extremely important.

The normal:
- repository layer
- builder
- executor
- handlers

continue operating exactly the same way.

---

# `fset()`

Virtual repository entries are registered through:

```python
fset(path, value)
```

Example:

```python
flow.fset(
    "summarize.jinja2",
    "Summarize this article"
)
```

This injects a repository entry before flow execution begins.

---

# Repository Paths Define Semantics

The `path` argument is extremely important.

It is not merely a filename.

The path defines:
- node identity
- node scope
- repository location
- config scope behavior
- dependency namespace
- variant interaction

Example:

```python
flow.fset(
    "analysis/deep/summarize.jinja2",
    ...
)
```

creates a node with semantic scope:

```text
analysis/deep/summarize
```

exactly as if the file physically existed there.

---

# Virtual Repository Entries Behave Like Real Files

Virtual entries are treated as ordinary repository entries.

This means:
- builders process them normally
- handlers execute them normally
- config scoping works normally
- `nget()` works normally
- outputs work normally
- variants work normally

There are no "special runtime nodes."

The repository simply contains additional entries.

---

# `fset()` Value Types

`fset()` supports three value types:

| Type | Meaning |
|---|---|
| `str` | Virtual file content |
| `callable` | Direct Python node injection |
| `Path` | Redirected external file |

---

# String-Based Virtual Nodes

Providing a string creates a fully virtual file.

Example:

```python
flow.fset(

    "summarize.jinja2",

    """
Summarize this text:

{{ iget("article") }}
"""
)
```

This behaves exactly as if:

```text
summarize.jinja2
```

physically existed inside the flow.

---

# Callable-Based Python Nodes

Providing a callable injects a Python node directly into the repository.

Example:

```python
from odyss_ai_flows import *


@node
async def summarize():

    article = await iget("article")

    return f"Summary: {article[:50]}"


flow.fset(
    "summarize.py",
    summarize
)
```

This creates a normal Python node without requiring a physical `.py` file.

The builder processes it exactly like filesystem Python nodes.

---

# Redirected External Files

Providing a `Path` creates a redirected repository entry.

Example:

```python
from pathlib import Path


flow.fset(

    "summarize.jinja2",

    Path(
        "../shared/summarize.jinja2"
    )
)
```

This causes:
- the node to exist inside the current flow
- while sourcing content from an external file

This is extremely useful for:
- reusable flow libraries
- shared orchestration modules
- centralized prompt repositories
- modular runtime composition

without physically copying files into flows.

---

# Redirected Files Are Repository-Level Composition

Redirected paths are not template includes.

They are repository-level remapping.

The resulting repository behaves as if the redirected file physically existed inside the current flow.

This distinction is important because:
- node scope changes
- repository semantics change
- config semantics follow the new flow
- orchestration identity follows the new flow

rather than the original physical file location.

---

# Runtime Scope Example

Example:

```python
flow.fset(

    "analysis/summarize.jinja2",

    Path(
        "../shared/summarize.jinja2"
    )
)
```

The resulting runtime node scope becomes:

```text
analysis/summarize
```

even though the physical file exists elsewhere.

---

# Virtual Outputs and Models

`fset()` is not limited to nodes.

It can also inject:
- `outputs.json`
- `.model` files
- future repository-managed file types

Example:

```python
flow.fset(

    "outputs.json",

    """
{
    "include": [
        "summary",
        "classification"
    ]
}
"""
)
```

This allows runtime output behavior customization.

---

# Example: Runtime Output Projection

Example:

```python
flow = PreparedFlow(
    base_path="article_flow"
)

flow.fset(

    "outputs.json",

    """
{
    "include": [
        "summary"
    ]
}
"""
)
```

The runtime repository now behaves as if the physical flow contained that `outputs.json`.

---

# Hybrid Composition Example

Filesystem flow:

```text
article_flow/
├── summarize.jinja2
└── classify.jinja2
```

Runtime augmentation:

```python
flow = PreparedFlow(
    base_path="article_flow"
)

flow.fset(
    "analysis.py",
    analysis_callable
)

flow.fset(

    "outputs.json",

    """
{
    "include": [
        "summary",
        "analysis"
    ]
}
"""
)
```

The resulting repository contains:
- physical nodes
- virtual nodes
- virtual outputs
- unified orchestration semantics

---

# Relationship to Variants

Variants and virtual flows are closely related conceptually.

Variants:
- overlay filesystem repository entries

Prepared flows:
- inject runtime repository entries

Both mechanisms ultimately operate at the repository layer.

---

# Current Config Limitation

Currently:

```python
fset("config.json", ...)
```

is intentionally unsupported.

Configuration virtualization is currently handled through:

```python
provided_tree=
```

instead.

---

# Current Config Behavior

When using:

```python
provided_tree=
```

filesystem config scanning becomes disabled for the flow.

This means:
- folder config files are ignored
- node config files are ignored

This behavior is documented separately in the configuration system documentation.

---

# Relationship to Prepared Runtime Config

`PreparedFlow` may optionally include:

```python
config_tree=
```

This allows repository virtualization and config virtualization to coexist within the same prepared flow structure.

---

# Runtime Repository Mutation Recording

`PreparedFlow` does not eagerly construct repositories.

Instead, it records repository mutations which are later applied during `run_flow()` initialization.

This keeps the architecture:
- lightweight
- unified
- repository-centric
- execution-consistent

without introducing alternate orchestration systems.

---

# Practical Use Cases

Typical usage includes:
- runtime-generated prompts
- orchestration augmentation
- reusable flow libraries
- testing infrastructure
- AI-generated orchestration
- temporary runtime nodes
- generated outputs
- dynamic orchestration assembly
- customer-specific orchestration overlays
- modular orchestration composition

---

# Why This Exists

The framework intentionally treats flows as:
- repository compositions
- execution structures
- orchestration graphs

rather than strictly physical folders.

This allows orchestration systems to remain:
- composable
- dynamic
- runtime-aware
- modular
- reusable

without abandoning explicit execution semantics.

---

# Design Philosophy

Virtual and hybrid flows intentionally preserve:
- explicit repository structure
- deterministic orchestration behavior
- normal builder semantics
- normal executor semantics
- ordinary handler execution

The framework does not create separate runtime systems for virtual orchestration.

Instead, it extends the repository abstraction itself.

This keeps:
- filesystem flows
- variants
- virtual flows
- hybrid flows

as different forms of the same underlying orchestration architecture.