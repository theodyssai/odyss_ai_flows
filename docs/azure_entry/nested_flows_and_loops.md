# Nested Flows and Loops

Flows can execute other flows.

This is one of the framework's primary composition mechanisms and is intentionally treated as a core architectural pattern rather than an advanced workaround.

Any Python node can call `run_flow()` to execute:
- another flow
- a reusable subflow
- a single node
- a dynamically selected flow
- iterative orchestration patterns
- recursive execution structures

This allows larger systems to be built from smaller composable flows instead of continuously expanding a single monolithic flow.

---

# Flows as Reusable Execution Units

The framework strongly encourages treating flows as reusable execution modules.

If a piece of orchestration:
- is non-trivial
- reusable
- repeated
- logically isolated
- independently testable

it will often be cleaner as its own flow.

This creates systems that are:
- easier to maintain
- easier to debug
- easier to test
- easier to evolve
- easier to reuse across projects

while preserving a consistent execution model.

---

# Basic Nested Flow Example

Example structure:

```text
main_flow/
├── orchestrator.py

subflows/
└── process_item/
    ├── prepare.jinja2
    ├── analyze.jinja2
    └── finalize.py
```

Contents of `orchestrator.py`:

```python
from odyss_ai_flows import *


@node
async def orchestrator():

    items = [
        "black holes",
        "quantum mechanics",
        "dark matter"
    ]

    results = []

    for item in items:

        subflow = await run_flow(
            "subflows/process_item",
            topic=item
        )

        results.append(
            subflow.outputs
        )

    return results
```

In this example:
- the parent flow orchestrates iteration
- the subflow handles reusable processing logic
- each execution receives independent runtime inputs
- the same subflow is reused multiple times

---

# Nested Flows Inside Loops

Nested flows work naturally inside loops.

Example:

```python
from odyss_ai_flows import *


@node
async def batch_processor():

    results = []

    for i in range(3):

        subflow = await run_flow(
            "subflows/process_item",
            iteration=i
        )

        results.append(
            subflow["final_result"]
        )

    return results
```

This allows:
- iterative execution
- dynamic orchestration
- batch processing
- fan-out execution
- recursive orchestration
- reusable workflow composition

without introducing separate orchestration systems.

---

# Flow Isolation

Nested flows are fully isolated execution contexts.

A subflow does not share:
- runtime inputs
- node state
- execution repository
- configuration repository
- file repository
- runtime context

with its parent flow unless explicitly passed through inputs or configuration.

This isolation is intentional and allows nested flows to remain composable and predictable.

Each nested flow behaves as an independent execution instance.

---

# Filesystem Independence

Parent and child flows are completely independent filesystem structures.

Subflows do not need to:
- exist inside the parent flow folder
- share folder hierarchy
- inherit filesystem organization
- participate in the parent's node namespace

A subflow is simply another executable flow.

This keeps reusable orchestration modules cleanly separable from the systems that invoke them.

---

# Strategy Inheritance

Execution strategies are automatically inherited by nested flows unless explicitly overridden.

This allows orchestration behavior to remain consistent across deeply nested execution trees without repeatedly configuring execution settings manually.

Advanced execution strategy customization is covered separately in dedicated documentation.

---

# Run Name Propagation

Run naming metadata is also propagated automatically through nested executions.

This helps preserve:
- observability
- execution tracing
- debugging consistency
- orchestration lineage

across complex nested execution systems.

Detailed run naming behavior is covered in dedicated runtime documentation.

---

# Error Propagation

Errors from nested flows propagate naturally to parent flows.

This means failures inside subflows:
- remain visible
- preserve execution causality
- integrate with flow failure handling
- participate in orchestration error propagation

without requiring special nested execution handling.

Detailed error propagation behavior is covered separately in error handling documentation.

---

# Accessing Nested Flow Results

`run_flow()` returns a normal `FlowResult`.

This means nested flows support:
- projected outputs
- `outputs.json`
- serialization
- output filtering
- mapped outputs
- status inspection
- error handling

exactly like top-level flows.

Example:

```python
subflow = await run_flow(
    "subflows/process_item",
    topic="black holes"
)

result = subflow["article"]
```

---

# Why Nested Flows Matter

Nested flow composition is one of the framework's most important scaling mechanisms.

Without nested flows, orchestration systems often become:
- monolithic
- repetitive
- difficult to refactor
- difficult to debug
- difficult to reuse

By treating flows as composable execution units, systems can evolve into:
- reusable orchestration libraries
- modular AI systems
- layered execution architectures
- reusable processing pipelines
- dynamic orchestration systems

while preserving a unified execution model.

---

# Unified Execution Model

A nested flow is still just a flow.

The same concepts continue to apply:
- `iget()`
- `nget()`
- outputs
- config scoping
- async orchestration
- concurrency
- runtime isolation
- handlers
- execution strategies

This consistency is intentional.

The framework avoids introducing separate orchestration models for:
- small flows
- nested systems
- loops
- reusable modules
- large execution architectures

allowing systems to scale incrementally without switching paradigms.