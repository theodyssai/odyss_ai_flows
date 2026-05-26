# Internal Architecture Explained

The framework is intentionally split into multiple lightweight subsystems with relatively flat responsibilities.

The goal of the architecture is not maximal abstraction, but:
- composability
- inspectability
- execution clarity
- low boilerplate
- extensibility
- async-first orchestration

---

# Package Structure

The framework is currently divided into:
- a provider-agnostic core package
- optional provider-specific integration packages

Core package:

```text
odyss_ai_flows
```

Current LLM integration package:

```text
odyss_ai_flows_azure
```

The Azure package contains Azure OpenAI-specific execution logic and can be installed as an optional dependency.

The core framework itself is intentionally provider-agnostic.

Its responsibility is orchestration and execution — not direct coupling to a specific LLM vendor.

This architecture allows the framework to eventually support:
- additional LLM providers
- local models
- multi-provider routing
- custom execution pipelines
- non-LLM node execution systems
- hybrid orchestration patterns

without redesigning the core runtime.

Additional integrations are planned on the roadmap, while custom integrations can already be implemented relatively easily through handlers and plugins.

---

# High-Level Execution Model

At a very high level, flow execution looks like this:

```text
Files -> Builder -> Nodes + Handlers -> Executor -> Runtime Result
```

Each subsystem is intentionally small and focused.

---

# Files Subsystem

The files subsystem is the foundation of flow composition.

Flows are expressed as compositions of files.

Those files may come from:
- the physical filesystem
- virtual sources
- generated sources
- hybrid layered systems
- variant overlays

The files subsystem abstracts all of these into a unified in-memory representation.

Its responsibilities include:
- recursive flow scanning
- node file discovery
- config discovery
- variant rebasing
- layered overrides
- metadata tracking
- source resolution

The rest of the framework does not need to know where files physically originated from.

---

# Config Subsystem

The config subsystem is an advanced scoped configuration system.

It allows configuration values to be resolved at multiple levels:
- globally
- per flow
- per folder scope
- per node
- per execution context
- dynamically at runtime

The system supports:
- layered merging
- override semantics
- variant-aware configuration
- lazy resolution
- provider references
- environment references
- secret references
- runtime overrides
- dynamically generated configuration trees

Configuration can be resolved:
- from within nodes
- externally from orchestration code
- from serialized trees
- from runtime execution contexts

The goal is allowing large systems to remain configurable without introducing excessive boilerplate or hardcoded infrastructure assumptions.

---

# Builder Subsystem

The builder is a lightweight subsystem responsible for converting file representations into executable flow structures.

Its responsibilities include:
- identifying node types
- assigning handlers
- constructing flow structures
- connecting dependency relationships
- resolving execution metadata

The builder intentionally performs minimal orchestration logic itself.

Its purpose is structural transformation, not execution.

---

# Executor Subsystem

The executor is the async orchestration engine responsible for executing nodes within a flow.

It manages:
- dependency ordering
- concurrency
- async scheduling
- node lifecycle
- result propagation
- execution state
- failure handling
- cancellation
- streaming coordination

The executor is intentionally designed around async execution from the ground up.

Concurrency is treated as a native execution concern rather than a later optimization layer.

---

# Handlers

Handlers define how nodes actually execute.

They are the execution units behind node behavior.

Different handler types can implement:
- Python execution
- Jinja rendering
- LLM interaction
- structured outputs
- streaming
- middleware pipelines
- custom orchestration logic
- external integrations

The handler system supports multiple composition approaches:
- inheritance
- middleware
- component-based execution pipelines

This allows execution logic to remain modular while avoiding excessively rigid abstractions.

Handlers are intentionally extensible and are one of the primary framework extension points.

---

# Runtime Subsystem

The runtime subsystem is responsible for actually running flows.

This includes:
- initializing execution context
- managing runtime-scoped state
- handling inputs
- selecting execution strategy
- assigning run metadata
- orchestrating nested runs
- collecting results
- constructing final flow outputs

The runtime acts as the coordination layer connecting all major subsystems together.

---

# Context Isolation

All major runtime state is scoped using `contextvars`.

This means:
- every flow run receives isolated runtime state
- nested flow executions are fully supported
- concurrent executions do not interfere with each other
- execution-local state can remain globally accessible within the current flow context

Subsystems such as:
- config
- inputs
- runtime metadata
- file repositories
- streaming buffers
- execution state

are all scoped per flow run.

This architecture allows arbitrary nested flow execution while preserving execution isolation and async safety.

---

# Architectural Goals

The architecture intentionally favors:
- explicit execution
- lightweight orchestration
- low dependency count
- composability
- inspectability
- async-first execution
- incremental extensibility

over:
- opaque orchestration layers
- deeply nested abstractions
- hidden execution behavior
- tightly coupled infrastructure

The framework is designed to remain understandable even as systems scale from:
- simple local experiments

to:

- distributed enterprise orchestration systems.