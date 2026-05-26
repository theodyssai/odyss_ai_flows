# What Is This?

This framework is an opinionated execution framework for orchestrating AI systems, primarily large language models (LLMs).

It is designed around a simple idea:

> AI systems should feel lightweight to experiment with, but should not collapse when they grow into real production infrastructure.

Most existing approaches force a tradeoff between:
- rapid experimentation and production robustness
- visual low-code simplicity and unrestricted engineering freedom
- flexible orchestration and predictable execution
- quick prototypes and maintainable systems

This framework attempts to minimize those tradeoffs instead of choosing one side.

---

# Core Philosophy

The framework follows a "low-code, code-only, unbounded-code" philosophy.

This means:
- simple things should require very little code
- complex things should still be possible without fighting the framework
- there should never be an artificial ceiling on system complexity
- developers should not need to abandon the framework when requirements become unusual

In practice, most simple flows can be expressed with extremely small amounts of code and configuration, while advanced systems can still use:
- custom Python logic
- dynamic execution
- looping
- concurrency
- persistent workflows
- human-in-the-loop orchestration
- streaming
- external integrations
- custom execution patterns

without escaping the framework.

---

# Designed for Fast Iteration

The framework is optimized for extremely fast prototyping and experimentation.

Flows are intentionally lightweight:
- minimal boilerplate
- implicit defaults
- filesystem-based structure
- automatic dependency wiring
- minimal infrastructure ceremony

The goal is to reduce the cost of trying ideas.

Developers should be able to:
- create experimental flows quickly
- restructure systems rapidly
- evolve prototypes into production systems incrementally
- reuse the same mental model across small and large workloads

---

# Flow and Node Oriented

The framework is centered around flows and nodes.

A flow is a graph of executable nodes:
- Python nodes
- Jinja/LLM nodes
- orchestration nodes
- durable execution nodes
- custom node types

Nodes are designed to remain composable and individually understandable, while flows can scale from:
- in-memory local execution

to:

- distributed long-running enterprise orchestration

using the same conceptual model.

---

# Async by Nature

The framework is fundamentally asynchronous.

Concurrency is not treated as an optional add-on, but as part of the execution model itself.

This enables:
- parallel execution
- high-throughput orchestration
- efficient I/O-heavy workloads
- scalable AI pipelines
- streaming systems
- long-running execution patterns

without redesigning application structure later.

---

# Production-Oriented Without Heavy Architecture

Although optimized for experimentation speed, the framework is also designed for production usage.

The architecture intentionally stays:
- relatively flat
- highly inspectable
- dependency-light
- explicit in execution behavior

instead of relying on deeply layered abstractions or opaque orchestration systems.

The same framework can support:
- quick local experiments
- APIs
- scheduled jobs
- persistent workflows
- human approval systems
- elastic cloud execution
- enterprise AI integrations

without requiring separate technology stacks.

---

# Extensible by Design

The framework is intentionally built to be extensible.

Developers can introduce:
- custom handlers
- plugins
- execution patterns
- node types
- middleware
- integrations
- infrastructure bindings

without modifying core concepts.

Most extensions require only small bootstrap changes rather than large framework forks.

---

# Unified Execution Model

One of the framework's core goals is unifying multiple execution styles under the same expression model.

The same flow concepts can be used for:
- local in-memory execution
- deterministic orchestration
- dynamic or agentic systems
- persistent durable execution
- long-running workflows
- human-in-the-loop systems
- elastic cloud scaling

without switching to an entirely different programming model.

---

# Opinionated, Not Restrictive

The framework is intentionally opinionated.

It strongly favors:
- explicit execution
- composability
- orchestration clarity
- engineering-first workflows
- predictable behavior

However, it attempts to avoid becoming restrictive.

The framework provides defaults, conventions, and structure — but tries to avoid imposing hard ceilings on what systems can ultimately become.