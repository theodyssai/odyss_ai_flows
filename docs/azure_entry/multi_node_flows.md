# Multi-Node Flows

Flows are not limited to a single node.

A flow can also be a folder containing multiple interconnected nodes which execute concurrently and dynamically resolve dependencies between one another.

This is one of the framework's core architectural concepts.

---

# Execution Model

Unlike traditional orchestration systems that build a fully static dependency graph before execution, this framework resolves dependencies dynamically during runtime.

At flow startup, all nodes are considered runnable.

Nodes begin execution concurrently and continue running until they request unresolved dependencies through `nget()`.

This creates a lightweight async execution model where:
- dependency resolution
- synchronization
- orchestration
- result retrieval

are unified into a single mechanism.

The result is:
- minimal orchestration boilerplate
- natural concurrency
- dynamic execution capabilities
- simple flow composition
- support for both deterministic and highly dynamic flows

without requiring separate orchestration definitions.

---

# What Is `nget()`?

`nget()` is the primary mechanism used to retrieve the result of another node.

Example:

```python
result = await nget("some_node")
```

If the target node:
- has already completed, the result is returned immediately
- is still running, execution pauses until the node finishes
- has not started yet, execution scheduling ensures it becomes runnable

This means `nget()` acts simultaneously as:
- dependency declaration
- dependency retrieval
- synchronization point
- execution coordination mechanism

---

# Jinja Integration

Inside Jinja nodes, `nget()` is automatically injected into the template context.

Although `nget()` is internally asynchronous, Jinja templates do not use `await`.

Example:

```jinja2
{{ nget("some_node") }}
```

not:

```jinja2
{{ await nget("some_node") }}
```

Awaiting is handled automatically by the framework's async Jinja execution layer.

This allows Jinja flows to remain visually simple while still participating fully in async orchestration.

---

# Example: Simple Multi-Node Flow

Consider the following flow structure:

```text
example_flow/
├── color.jinja2
├── fruit.jinja2
└── description.jinja2
```

Contents of `color.jinja2`:

```jinja2
Give a random color.
```

Contents of `fruit.jinja2`:

```jinja2
Give a random fruit matching this color:

{{ nget("color") }}
```

Contents of `description.jinja2`:

```jinja2
What can you tell me about this fruit?

{{ nget("fruit") }}
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

Conceptually, execution proceeds like this:

1. The framework scans the folder and identifies all nodes.

2. All nodes become runnable immediately.

3. `color.jinja2` executes independently because it has no dependencies.

4. `fruit.jinja2` begins execution but pauses on:

```jinja2
{{ nget("color") }}
```

until `color` finishes.

5. Once `color` completes, `fruit` resumes execution.

6. `description.jinja2` similarly pauses on:

```jinja2
{{ nget("fruit") }}
```

until `fruit` completes.

7. The flow finishes once all runnable nodes complete successfully.

This execution model naturally enables concurrency without requiring explicit orchestration code.

---

# Why This Model Exists

The framework intentionally avoids large centralized orchestration definitions.

Instead, dependencies are expressed directly where values are needed.

This creates flows that are:
- lightweight
- composable
- easy to refactor
- naturally concurrent
- dynamically executable

while still scaling to:
- complex orchestration systems
- looping execution
- durable workflows
- agentic systems
- human-in-the-loop execution
- distributed cloud architectures

using the same fundamental execution model.

---

# Python Nodes vs Jinja Nodes

Both Python and Jinja nodes use the same dependency mechanism.

Python nodes use explicit async syntax:

```python
result = await nget("other_node")
```

Jinja nodes use implicit awaiting:

```jinja2
{{ nget("other_node") }}
```

This allows both node types to participate in the same async orchestration system while remaining idiomatic to their respective environments.