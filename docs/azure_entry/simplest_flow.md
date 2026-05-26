# Run the Simplest Flow

The framework is fully asynchronous and execution-oriented by design.

Flows are constructed only for the duration of a single execution and are not persisted between runs. Internally, the framework uses non-blocking async execution patterns and async Azure OpenAI calls.

There is no global runtime state shared between flows. Apart from logging infrastructure and intentionally cached low-level service clients, flows execute independently and do not interfere with one another.

This allows:
- multiple flows to run concurrently
- lightweight local experimentation
- scalable cloud execution
- efficient I/O-heavy orchestration
- long-running async workloads

without changing the programming model.

---

# What Constitutes a Flow?

A flow can be:
- a single node file
- or a folder containing multiple node files

Currently, the framework includes built-in support for:
- `.py` Python nodes
- `.jinja2` Jinja/LLM nodes

However, the architecture is intentionally extensible and additional node types can be added through custom handlers and file matchers.

---

# Prerequisites

Before running flows, create a `global_config.json` file in the root directory of your project.

Example:

```json
{
  "azure_openai": {
    "endpoint": "<your_azure_endpoint>",
    "api_version": "<your_api_version>",
    "deployment_name": "<your_deployment_name>",
    "api_key": "<your_api_key>"
  }
}
```

This is the simplest default configuration for Azure OpenAI usage.

The configuration system is hierarchical and significantly more powerful than this minimal example, but this is enough to begin running flows immediately.

---

# Example: Running a Simple Flow

Below is the simplest possible executable flow:

```python
from odyss_ai_flows import run_flow
import asyncio


async def run_hello_world_flow():
    flow = await run_flow("hello_world.jinja2")

    print(flow)


asyncio.run(run_hello_world_flow())
```

Contents of `hello_world.jinja2`:

```jinja2
Hello world!
```

This flow sends the prompt:

```text
Hello world!
```

to the configured LLM deployment and executes fully asynchronously.

Although extremely small, this example already demonstrates the framework's core execution model:
- flows are lightweight
- nodes are directly executable
- orchestration is async by default
- filesystem structure defines the flow
- minimal boilerplate is required

From this point, flows can evolve incrementally into:
- multi-node systems
- Python-integrated orchestration
- streaming pipelines
- durable workflows
- human-in-the-loop systems
- dynamic or agentic execution patterns
- production cloud architectures

without changing the underlying conceptual model.