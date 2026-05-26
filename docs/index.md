# Odyss AI Flows

Odyss AI Flows is an opinionated orchestration framework for building AI and LLM systems through composable flows and nodes.

The framework focuses on:
- extremely low boilerplate
- explicit orchestration
- async-first execution
- composability
- enterprise-grade scalability
- provider extensibility
- unified execution semantics

while remaining lightweight and fully code-oriented.

---

# Documentation Status

This documentation is currently in active development.

The current version focuses primarily on:
- execution concepts
- architecture
- orchestration semantics
- Azure OpenAI integration
- extensibility mechanisms

Further refinement, examples, and ecosystem documentation will be added incrementally.

---

# Recommended Starting Points

If you are new to the framework, begin with:

- `simplest_flow.md`
- `multi_node_flows.md`

These pages introduce:
- basic execution
- node relationships
- flow composition
- `nget()`
- async orchestration semantics

before moving into more advanced topics.

---

# Suggested Learning Order

Recommended progression:

1. Simplest Flow
2. Multiple Node Flows
3. Python Nodes
4. Flow Inputs
5. Flow Outputs
6. Nested Flows and Loops
7. Config System and `cget()`
8. Azure OpenAI Connections
9. Pipelines and Composed Handlers
10. Structured Outputs and Actions

After that:
- variants
- virtual flows
- middleware
- runtime strategies
- extension points

become much easier to understand.

---

# Core Architectural Philosophy

The framework intentionally treats AI as:
- an execution component
- not a platform
- not an opaque agent runtime
- not a hidden orchestration engine

Flows remain:
- explicit
- inspectable
- composable
- provider-independent

while still supporting:
- structured outputs
- actions
- streaming
- multimodal execution
- long-running orchestration
- dynamic execution behavior

inside a unified execution model.

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
- multimodal support
- streaming
- actions
- Azure authentication integration

through the composed pipeline architecture.

---

# Design Goals

The framework attempts to achieve a specific balance:

- minimal experimentation overhead
- no artificial complexity ceiling
- explicit orchestration semantics
- low operational friction
- extensibility without framework rewrites

This leads to a system that can scale from:
- very small prompt experiments
- to complex enterprise orchestration systems

without changing the underlying execution model.

---

# Important Concept

Flows are intentionally treated as:
- composable execution graphs
- rather than hidden autonomous runtimes

This distinction influences nearly every architectural decision throughout the framework.