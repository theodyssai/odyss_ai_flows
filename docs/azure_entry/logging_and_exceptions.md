# Logging and Errors

The framework includes a lightweight execution-aware logging and error handling system designed specifically for orchestration-heavy async workflows.

The goal is not to provide a massive observability platform, but rather:
- readable execution tracing
- useful debugging context
- nested flow visibility
- execution lineage awareness
- minimal operational boilerplate

The system is intentionally optimized for understanding complex orchestration behavior during development and production debugging.

---

# Execution-Aware Logging

Logging automatically includes execution context information.

Every log entry can automatically contain:
- run identity
- nested execution lineage
- module or subsystem location

without requiring manual logger propagation through flows or nodes.

Example log output:

```text
[daily_article_generation] [executor/runner] Starting flow execution

[daily_article_generation, nested in: summarize, index: 0] [handlers/jinja] Rendering template

[daily_article_generation] [executor/node_execution_state] Node completed successfully
```

This behavior works automatically across:
- nested flows
- loops
- concurrent executions
- reusable subflows

using execution-local runtime context.

---

# Run Context Integration

The logger automatically injects the current runtime execution name into log records.

This means:
- top-level flows remain identifiable
- nested flows inherit lineage
- loop iterations become distinguishable
- concurrent executions remain readable

without manually passing tracing objects or logger instances.

Run naming behavior is covered separately in dedicated runtime documentation.

---

# Log Structure

The default logger format is intentionally compact and human-oriented.

Typical structure:

```text
[run_name] [path_label] message
```

Example:

```text
[article_pipeline] [builder/builder] Initializing flow structure
```

The logger intentionally prioritizes:
- readability
- orchestration inspection
- debugging clarity
- local development usability

over large structured telemetry payloads.

---

# Path Labels

The logger automatically shortens module paths into compact labels.

Example:

```text
[config/api]
[executor/runner]
[handlers/jinja]
[builder/builder]
```

This keeps logs readable while still preserving subsystem locality.

---

# Colored Console Logging

By default, the framework automatically attaches a colored console logger when no root logging configuration exists.

This provides:
- readable local debugging
- colored severity levels
- minimal setup experience

without requiring manual logging bootstrap code.

If the hosting application already configures logging, the framework integrates into the existing logging system instead of attaching duplicate handlers.

---

# Log Configuration

Logging behavior can be configured through environment variables.

Example:

```text
ODYSS_FLOWS_LOG_LEVEL=INFO
```

Supported levels:

```text
DEBUG
INFO
WARNING
ERROR
CRITICAL
```

---

# Log Truncation

AI systems frequently produce extremely large:
- prompts
- outputs
- serialized contexts
- debugging payloads

To prevent logs from becoming unreadable, the framework truncates long log messages by default.

Example:

```text
ODYSS_FLOWS_LOG_MAX_LENGTH=500
```

Default:

```text
500
```

Disable truncation entirely:

```text
ODYSS_FLOWS_LOG_MAX_LENGTH=-1
```

This is especially useful during prompt debugging or deep orchestration inspection.

---

# Exception Model

The framework intentionally separates different categories of failures.

Primary exception types:

- `NodeExecutionError`
- `FrameworkError`
- `FlowBreak`

This separation helps preserve execution semantics and debugging clarity.

---

# `NodeExecutionError`

`NodeExecutionError` represents failures originating from node execution logic.

Example causes:
- Python exceptions inside nodes
- template rendering failures
- LLM execution failures
- orchestration logic errors
- external API failures

The exception automatically includes:
- node scope
- execution run name
- original exception

Example:

```text
[daily_article_generation] Node 'summarize/article' failed: ValueError(...)
```

This makes failures significantly easier to localize inside large orchestration systems.

---

# `FrameworkError`

`FrameworkError` represents failures originating from the framework runtime itself rather than user node logic.

Example causes:
- builder failures
- runtime initialization failures
- invalid framework state
- infrastructure orchestration failures
- repository initialization problems

Example:

```text
[daily_article_generation] Framework error: RuntimeError(...)
```

This separation helps distinguish:
- orchestration infrastructure failures

from:

- business logic or node failures

during debugging and observability.

---

# `FlowBreak`

`FlowBreak` is a special orchestration control-flow mechanism.

It intentionally does not represent a framework failure.

Typical usage includes:
- approval systems
- human-in-the-loop orchestration
- intentional execution pauses
- orchestration exits
- durable execution interruption

Example:

```text
[daily_article_generation] Waiting for approval (scope: review_node)
```

Unlike ordinary exceptions, `FlowBreak` is treated as intentional orchestration behavior rather than an execution error.

---

# Error Propagation

Errors propagate naturally through nested flow execution.

This means:
- nested subflow failures remain visible
- execution lineage is preserved
- run names remain attached
- orchestration causality remains understandable

without requiring custom propagation logic.

Nested flow error behavior is covered in more detail in dedicated execution documentation.

---

# Exception Context

Framework exceptions intentionally preserve execution context information.

This includes:
- run name
- node scope
- original exception
- nested execution lineage

This becomes especially important once systems begin using:
- nested flows
- loops
- fan-out execution
- concurrent orchestration
- durable execution
- reusable subflows

where ordinary Python stack traces often become difficult to interpret.

---

# Practical Debugging Benefits

The framework intentionally attempts to make orchestration systems operationally understandable without introducing heavy tracing infrastructure.

Combined together:
- run naming
- execution-aware logging
- scoped exceptions
- nested lineage propagation
- path labels
- automatic context injection

create lightweight but highly practical orchestration observability.

This is especially useful during:
- rapid prototyping
- debugging
- production incident analysis
- orchestration development
- reusable subflow inspection
- nested execution tracing

without requiring separate tracing systems for basic execution visibility.

---

# Design Philosophy

The framework intentionally favors:
- explicit execution visibility
- lightweight observability
- execution lineage preservation
- readable orchestration logs
- low operational overhead

over:
- opaque orchestration behavior
- deeply hidden runtime state
- excessive telemetry boilerplate
- mandatory external tracing infrastructure

The result is a system designed to remain operationally understandable even as orchestration complexity grows significantly.