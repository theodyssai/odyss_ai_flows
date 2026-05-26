# Images in LLM Nodes

The framework supports image-aware LLM execution directly inside ordinary Jinja nodes.

Images are integrated into the same rendering and pipeline system used for text execution.

This means:
- image handling is fully optional
- image support uses ordinary Jinja syntax
- multimodal execution remains pipeline-native
- images participate naturally in composed handler execution

without introducing separate orchestration systems or special node types.

---

# The Core Idea

Images are collected during prompt rendering and later consumed by compatible pipeline components.

This is extremely important.

The renderer itself:
- does not call the LLM
- does not perform provider-specific execution
- only prepares execution state

Later pipeline stages transform that state into provider-specific message formats.

---

# The `img()` Helper

Images are added through:

```jinja2
{{ img(...) }}
```

Example:

```jinja2
Analyze this image:

{{ img("diagram.png") }}
```

The image becomes part of the current LLM node execution context.

---

# Example: Local Image

Example:

```jinja2
Describe the architecture shown here:

{{ img("architecture.png") }}
```

The renderer:
- reads the file
- converts it to base64
- creates a data URI
- stores it in handler state

The Azure message builder later converts it into OpenAI-compatible image message parts.

---

# Example: Remote URL

Example:

```jinja2
Analyze this image:

{{ img("https://example.com/image.png") }}
```

URLs are passed directly without local encoding.

---

# Example: Data URI

Example:

```jinja2
{{ img("data:image/png;base64,...") }}
```

Pre-encoded image payloads are also supported directly.

---

# How Image Handling Works

Image support is implemented through the rendering pipeline component.

During rendering:
- images are collected
- image references are normalized
- image payloads are stored in handler state

The renderer itself does not:
- format provider messages
- perform API calls
- decide provider semantics

This separation is intentional.

---

# Renderer Responsibilities

The renderer is responsible for:
- prompt rendering
- Jinja execution
- image collection
- structured output helpers
- action helpers
- skip semantics

Example renderer helpers:

```jinja2
{{ img(...) }}

{{ skip() }}

{{ model(...) }}

{{ actions(...) }}
```

All of these operate during rendering before actual LLM execution begins.

---

# Pipeline Consumption

Later pipeline stages consume the rendered image state.

Example Azure message builder behavior:

```python
parts.append(
    {
        "type": "image_url",
        "image_url": {
            "url": img["image"]
        }
    }
)
```

This converts renderer image segments into Azure/OpenAI-compatible multimodal message parts.

---

# Why This Separation Exists

The renderer intentionally remains provider-agnostic.

It only produces abstract execution state:
- rendered text
- images
- models
- actions

Provider-specific caller components later interpret that state.

This allows:
- reusable rendering behavior
- provider-independent orchestration
- modular multimodal support
- future provider extensibility

without coupling rendering directly to Azure APIs.

---

# Local File Encoding

When using local files:

```jinja2
{{ img("photo.png") }}
```

the renderer:
- reads the file
- base64-encodes it
- automatically generates the proper MIME-prefixed data URI

Supported automatic MIME handling currently includes:
- PNG
- JPEG/JPG

---

# Relative Paths

Local image paths are resolved relative to the current execution environment.

Example:

```jinja2
{{ img("images/chart.png") }}
```

works like ordinary filesystem references.

---

# Multiple Images

Multiple images may be attached within the same node.

Example:

```jinja2
Compare these diagrams:

{{ img("diagram_1.png") }}

{{ img("diagram_2.png") }}
```

The message builder converts all collected images into multimodal message parts.

---

# Images and Text Together

Images naturally coexist with ordinary prompt text.

Example:

```jinja2
Analyze this dashboard screenshot.

Focus on:
- anomalies
- trends
- possible system failures

{{ img("dashboard.png") }}
```

The resulting message contains:
- text content
- image content
- multimodal structure

inside a single LLM request.

---

# Images and Structured Outputs

Images work together with structured outputs.

Example:

```jinja2
{{ model(ImageAnalysisResult) }}

Analyze this diagram:

{{ img("architecture.png") }}
```

This allows:
- multimodal structured extraction
- visual classification
- diagram analysis
- screenshot parsing
- visual metadata extraction

inside ordinary orchestration flows.

---

# Images and Actions

Images also work together with action systems.

Example:

```jinja2
{{ actions(search_docs) }}

Analyze this screenshot and search for matching incidents:

{{ img("incident.png") }}
```

This allows:
- multimodal reasoning
- visual workflows
- action-triggered analysis
- image-aware orchestration

inside the same execution model.

---

# Images and Streaming

Image-aware execution also works with streaming pipelines.

The image handling itself occurs during rendering before:
- streaming begins
- provider execution starts

Streaming behavior therefore remains fully compatible with multimodal requests.

---

# Provider Compatibility

Image support depends on:
- the active caller component
- the underlying provider capabilities
- the selected deployment/model

The renderer itself always supports image collection, but actual multimodal execution depends on the provider pipeline.

---

# Current Azure Behavior

The Azure extension currently converts collected image segments into Azure OpenAI multimodal message payloads automatically.

This means ordinary Jinja nodes may already support:
- image analysis
- screenshot reasoning
- multimodal structured extraction
- visual workflows

when using compatible Azure OpenAI deployments.

---

# Example: Screenshot Analysis Flow

Example:

```jinja2
Analyze this screenshot.

Identify:
- visible problems
- possible root causes
- unusual behavior

{{ img("server_dashboard.png") }}
```

No special multimodal node type is required.

---

# Example: Diagram Extraction

Example:

```jinja2
{{ model(ArchitectureSummary) }}

Extract architecture information from this diagram:

{{ img("architecture.png") }}
```

The pipeline automatically combines:
- multimodal messages
- structured outputs
- Azure execution

inside a single orchestration step.

---

# Relationship to the Pipeline System

Images are fundamentally pipeline-native.

The execution process becomes:

```text
render
    ↓
collect images
    ↓
build multimodal messages
    ↓
provider execution
```

This keeps multimodal behavior:
- composable
- provider-aware
- extensible
- execution-consistent

without requiring separate orchestration systems.

---

# Design Philosophy

The framework intentionally treats multimodal execution as:
- an extension of ordinary orchestration
- part of normal handler pipelines
- part of repository-native execution

rather than introducing:
- special image runtimes
- isolated multimodal APIs
- separate orchestration engines

This keeps image-aware flows:
- lightweight
- composable
- explicit
- consistent with text orchestration

while still supporting sophisticated multimodal execution behavior through the existing pipeline architecture. :contentReference[oaicite:0]{index=0}