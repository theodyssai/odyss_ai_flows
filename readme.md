# Odyss AI Flows

Opinionated async orchestration framework for AI and LLM systems.

The framework focuses on:
- composable flows and nodes
- extremely low boilerplate
- async-first execution
- explicit orchestration semantics
- provider extensibility
- structured outputs
- actions
- multimodal execution
- enterprise-grade scalability

without introducing opaque orchestration platforms or hidden agent runtimes.

---

# Project Status

The framework is currently in active development.

At this stage:
- APIs may evolve rapidly
- architectural refinement is ongoing
- documentation is still incomplete
- some extension surfaces may change

The repository is expected to remain private for at least several additional development iterations before public release.

Backward compatibility should not yet be assumed.

---

# Documentation

Documentation currently exists as MkDocs-based markdown pages under:

```text
/docs
```

To build and preview documentation locally:

```bash
mkdocs serve
```

Then open:

```text
http://127.0.0.1:8000
```

---

# Early Documentation Scope

Current documentation primarily focuses on:
- orchestration concepts
- execution semantics
- architecture
- Azure integration
- pipelines
- actions
- extensibility

The documentation is intentionally being developed incrementally.

Examples, diagrams, tutorials, and ecosystem integrations will be expanded over future iterations.

---

# Recommended Starting Points

Begin with:

```text
docs/simplest_flow.md
docs/multi_node_flows.md
```

These introduce:
- flows
- nodes
- `nget()`
- async orchestration
- execution semantics

before moving into advanced architecture topics.

---

# Philosophy

The framework intentionally treats AI as:
- an execution component
- not a platform
- not an opaque orchestration runtime

The goal is to preserve:
- explicit orchestration
- inspectability
- composability
- operational control

while still supporting sophisticated AI workflows.

---

# Current Provider Support

The core framework is provider-agnostic.

The primary production-ready integration currently available is:

```text
odyss_ai_flows_azure
```

which provides:
- Azure OpenAI execution
- structured outputs
- streaming
- multimodal execution
- actions
- Azure authentication integration

through the composed handler pipeline architecture.

---

# License

This project is licensed under the Apache License 2.0.

See:

```text
LICENSE
NOTICE
```

for details.

---

# Important Note

This repository currently prioritizes:
- architecture
- execution semantics
- extensibility
- orchestration correctness

over:
- polished UX
- stable APIs
- finalized ecosystem integrations

Rapid iteration and refactoring are expected during the current development stage.