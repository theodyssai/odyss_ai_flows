# Python Nodes

Although Jinja nodes are often the simplest way to create LLM-powered flows, Python nodes allow flows to include arbitrary execution logic.

Python nodes can be used for:
- data transformation
- orchestration
- external API calls
- dynamic execution logic
- conditional behavior
- custom integrations
- runtime computation
- nested flow execution
- advanced async workflows

The framework intentionally treats Python as a first-class orchestration language rather than a limited plugin mechanism.

---

# Python Nodes and `nget()`

Just like Jinja nodes, Python nodes use `nget()` to retrieve the results of other nodes.

Example:

```python
result = await nget("some_node")
```

Dependencies are not declared through function arguments.

Instead, dependencies are resolved dynamically during execution through explicit `nget()` calls.

This means Python nodes participate fully in the same async execution model as Jinja nodes:
- concurrent startup
- dynamic dependency resolution
- runtime synchronization
- async orchestration

---

# Defining a Python Node

Python nodes are defined using the `@node` decorator.

Example:

```python
from odyss_ai_flows import *


@node
async def process_color():
    color = await nget("color")

    return f"processed {color}"
```

The `@node` decorator is required.

Unlike older framework versions, Python nodes are no longer inferred automatically from top-level functions.

This makes node declaration explicit and allows Python files to contain:
- helper functions
- utility logic
- imports
- internal abstractions
- reusable components

without ambiguity.

---

# Import Surface

Most commonly used framework functionality is available through:

```python
from odyss_ai_flows import *
```

This intentionally exposes the primary orchestration surface directly.

Typical imports include:
- `@node`
- `run_flow`
- `nget`
- `iget`
- `cget`
- execution helpers
- runtime helpers

allowing node files to remain compact and lightweight.

---

# Example: Python + Jinja Flow

Consider the following flow structure:

```text
example_flow/
├── color.jinja2
├── process_color.py
└── description.jinja2
```

Contents of `color.jinja2`:

```jinja2
Give a random color.
```

Contents of `process_color.py`:

```python
from odyss_ai_flows import *


@node
async def process_color():
    color = await nget("color")

    return f"processed {color}"
```

Contents of `description.jinja2`:

```jinja2
What can you tell me about this color?

{{ nget("process_color") }}
```

Running the flow:

```python
from odyss_ai_flows import run_flow
import asyncio


async def run_multi_node_flow():
    flow = await run_flow("example_flow")

    print(flow)


asyncio.run(run_multi_node_flow())
```

---

# What Happens During Execution?

Execution proceeds dynamically:

1. All nodes become runnable.

2. `color.jinja2` executes immediately because it has no dependencies.

3. `process_color.py` starts execution but pauses on:

```python
await nget("color")
```

until the `color` node completes.

4. Once `color` finishes, `process_color` resumes and returns the transformed result.

5. `description.jinja2` pauses on:

```jinja2
{{ nget("process_color") }}
```

until the Python node completes.

6. The flow finishes once all runnable nodes complete successfully.

This allows Python and Jinja nodes to participate in the exact same orchestration model.

---

# Async Execution

Python nodes can be synchronous or asynchronous, but async nodes are strongly recommended.

Example async node:

```python
from odyss_ai_flows import *


@node
async def my_node():
    result = await nget("other_node")

    return result
```

Because the framework is async-first internally, async Python nodes integrate naturally with:
- concurrency
- streaming
- external APIs
- durable execution
- nested flows
- async orchestration

without blocking the executor.

---

# Beyond Simple Processing

Python nodes are intentionally unrestricted.

They are not limited to lightweight transformations.

A Python node may:
- orchestrate multiple dependencies
- dynamically choose execution paths
- call external systems
- execute nested flows
- manage streaming
- trigger actions
- coordinate durable workflows
- construct runtime state
- implement custom orchestration logic

This allows flows to evolve incrementally from simple prompt chains into fully custom execution systems without abandoning the framework's execution model.