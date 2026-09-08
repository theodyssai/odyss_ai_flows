# Composed Handlers and Pipelines

The framework uses a composed pipeline-based execution architecture for LLM nodes.

Instead of relying on:
- monolithic handler classes
- deeply specialized inheritance trees
- hardcoded provider runtimes
- opaque execution engines

LLM execution is assembled dynamically from reusable execution components.

This architecture allows the framework to remain:
- modular
- extensible
- provider-agnostic
- execution-oriented
- runtime-configurable

while still preserving explicit orchestration semantics.

---

# The Core Idea

An LLM node is not executed by:
- a single Azure handler
- a single OpenAI wrapper
- a monolithic orchestration engine

Instead, execution is performed through a pipeline of components.

Example:

```text
render
    ↓
messages_role
    ↓
action_model
    ↓
call_azure
    ↓
token_counter
    ↓
action_execute
```

Each stage contributes a specific execution behavior.

---

# Why This Exists

Simple prompt execution is only one part of modern orchestration systems.

Real production workflows often require:
- prompt rendering
- structured outputs
- streaming
- image handling
- action execution
- token accounting
- finish reason logging
- post-processing
- adaptive execution modes

The framework therefore treats LLM execution as:
- a composable runtime pipeline
- rather than a single provider call

---

# Fully Optional Complexity

Most users do not need to interact with pipelines directly.

The default pipelines are designed to work out-of-the-box for typical usage.

Simple flows continue working normally:

```jinja2
Summarize this article:

{{ iget("article") }}
```

No pipeline configuration is required.

The composed architecture exists to:
- enable extensibility
- support advanced execution behavior
- allow plugin ecosystems
- avoid monolithic handler designs

without increasing complexity for ordinary usage.

---

# Handler Components

Each pipeline stage is implemented as a handler component.

All components inherit from:

```python
LLMHandlerComponent
```

Example:

```python
class TokenCounter(
    LLMHandlerComponent
):
    async def run(self, data):
        ...
```

Each component:
- receives the shared handler instance
- may read or modify runtime state
- may transform execution behavior
- may enrich execution context
- may short-circuit execution

---

# Shared Handler State

Components cooperate through shared handler state.

Examples include:
- rendered prompt text
- structured output model
- action definitions
- messages
- images
- streaming state
- execution results

This allows pipelines to behave as:
- cooperative execution assemblies
- rather than isolated middleware transforms

---

# Pipeline-Based Execution

Pipelines are ordered execution stage lists.

Example Azure pipeline:

```python
"azure_default": [

    "render",

    "messages_role",

    "action_model",

    "call_azure",

    "finish_reason_logger",

    "token_counter",

    "action_execute",
]
```

Execution proceeds sequentially:
- each component runs
- shared handler state evolves
- later components build on earlier phases

---

# Default Azure Pipelines

The Azure extension currently contributes two primary pipelines:

| Pipeline | Purpose |
|---|---|
| `azure_default` | normal adaptive execution |
| `azure_streaming` | streaming execution |

---

# Default Azure Pipeline

The default Azure pipeline:

```python
[
    "render",
    "messages_role",
    "action_model",
    "call_azure",
    "finish_reason_logger",
    "token_counter",
    "action_execute",
]
```

provides:
- prompt rendering
- role-aware message formatting
- optional structured action modeling
- Azure OpenAI execution
- finish reason inspection
- token accounting
- optional action execution

---

# Streaming Pipeline

The streaming pipeline:

```python
[
    "render",
    "messages_role",
    "call_azure_streaming",
    "finish_reason_logger",
    "token_counter",
]
```

uses a streaming caller component instead of the normal Azure caller.

Importantly:
- streaming is not a separate runtime system
- streaming is simply a different execution pipeline

---

# Pipeline Selection

Pipelines are selected dynamically through scoped configuration.

Example:

```json
{
  "llm": {
    "pipeline": "azure_streaming"
  }
}
```

This may be configured:
- globally
- per flow
- per folder
- per node
- through variants
- through runtime overrides

like any other configuration value.

---

# Automatic Pipeline Selection

If no explicit pipeline is configured, the framework automatically selects a suitable default.

Behavior adapts based on:
- installed plugins
- structured output presence
- available components

This allows most users to avoid explicit pipeline configuration entirely.

The default is chosen deterministically:

1. Each installed plugin contributes one **default pipeline**:
   - its sole registered pipeline, if it registered exactly one;
   - otherwise the pipeline whose name ends with `_default`
     (e.g. the Azure extension's `azure_default`);
   - otherwise — if there is no `_default`, or more than one — the
     alphabetically-first of that plugin's pipelines.
2. Across all installed plugins, the **alphabetically-first** of those
   per-plugin defaults wins (qualified by plugin name, so e.g.
   `odyss_ai_flows_anthropic.*` precedes `odyss_ai_flows_azure.*`).
3. If no LLM plugin is installed at all, the framework falls back to its
   minimal core `structured` / `default` pipeline.

A single installed plugin therefore becomes the default automatically with
no configuration; with several installed, alphabetical order decides.

---

# Structured Outputs as Pipeline Semantics

Structured outputs are implemented as pipeline behavior rather than special node types.

Example:

```jinja2
{{ model(MyStructuredModel) }}

Analyze this article:
```

This causes:
- the renderer to register a model
- later pipeline stages to adapt automatically
- the Azure caller to switch into structured mode

No separate orchestration system is required.

---

# Actions as Pipeline Semantics

The action system is also pipeline-native.

Example:

```jinja2
{{ actions(search_web, save_result) }}

Find relevant information.
```

This triggers:
- dynamic structured schema generation
- structured LLM response handling
- optional action execution
- concurrent action processing

through ordinary pipeline stages.

---

# Adaptive Caller Components

Azure caller components are adaptive.

The same caller may:
- use plain text generation
- use structured outputs
- process action schemas
- support images
- support multimodal inputs

depending on runtime state prepared by earlier pipeline stages.

This allows pipelines to remain lightweight while still supporting sophisticated execution behavior.

---

# Pipeline Components Contributed by Plugins

Plugins contribute components through Python entry points.

Example:

```toml
[project.entry-points."odyss_ai_flows.llm_components"]

call_azure =
    "odyss_ai_flows_azure.handlers.callers.azure:AzureCaller"

token_counter =
    "odyss_ai_flows_azure.handlers.components.token_counter:TokenCounter"
```

This allows:
- automatic plugin discovery
- provider-independent architecture
- reusable execution components
- modular extension ecosystems

without modifying the core framework.

---

# Plugin Pipelines

Plugins may also contribute complete pipelines.

Example:

```toml
[project.entry-points."odyss_ai_flows.llm_pipelines"]
```

This allows extensions to provide:
- execution patterns
- provider-specific orchestration
- specialized streaming modes
- custom execution stacks

through ordinary plugin installation.

---

# User-Defined Pipelines

Users may also define pipelines directly in configuration.

Example:

```json
{
  "llm": {
    "pipelines": {

      "minimal": [
        "render",
        "call_azure"
      ],

      "streaming_debug": [
        "render",
        "messages_role",
        "call_azure_streaming",
        "token_counter"
      ]
    }
  }
}
```

These pipelines may then be selected normally:

```json
{
  "llm": {
    "pipeline": "minimal"
  }
}
```

---

# Custom Components

Users may register custom components programmatically.

Example:

```python
register_handler_component(
    "custom_logger",
    CustomLoggerComponent
)
```

Pipelines may then reference them:

```json
{
  "llm": {
    "pipelines": {

      "custom": [
        "render",
        "custom_logger",
        "call_azure"
      ]
    }
  }
}
```

---

# Skip Semantics Inside Pipelines

The rendering stage may intentionally abort execution through:

```jinja2
{{ skip() }}
```

If triggered:
- rendering stops
- the handler is marked as skipped
- remaining pipeline stages are bypassed
- no LLM call occurs

This allows pipelines to support conditional execution cleanly.

---

# Images and Multimodal Inputs

The rendering pipeline also supports image collection through:

```jinja2
{{ img("diagram.png") }}
```

or:

```jinja2
{{ img("https://...") }}
```

Images become part of shared handler state and are later processed by compatible caller components.

---

# Design Philosophy

The composed pipeline architecture intentionally avoids:
- monolithic orchestration handlers
- opaque execution engines
- provider-coupled runtime systems
- hidden agentic loops

Instead, execution is assembled explicitly from reusable execution phases.

This preserves:
- modularity
- extensibility
- explicit behavior
- provider independence
- execution transparency

while still supporting:
- structured outputs
- actions
- streaming
- multimodal execution
- advanced orchestration augmentation

inside a unified execution model.

---

# Most Users Should Use Defaults

Despite the flexibility of the pipeline system, most users should simply use the default pipelines initially.

The framework is designed so that:
- simple prompt execution remains extremely lightweight
- advanced capabilities remain optional
- orchestration complexity scales gradually
- custom execution behavior can be introduced incrementally

You only need to customize pipelines when your orchestration requirements genuinely demand it.

The default Azure pipelines are already designed to cover the majority of real-world production scenarios.