# Azure OpenAI Connections and Inference Configuration

The Azure integration layer is fully configuration-driven.

Nodes do not:
- construct Azure clients directly
- hardcode deployments
- hardcode authentication
- hardcode inference parameters

Instead, handlers resolve Azure connection profiles dynamically through scoped configuration.

This is one of the core architectural principles of the framework.

---

# Configuration-Driven LLM Execution

LLM execution behavior is determined through:
- connection profiles
- scoped configuration
- inheritance
- runtime overrides
- variants

rather than being embedded directly into node code.

This allows:
- infrastructure separation
- orchestration reuse
- deployment specialization
- environment flexibility
- runtime adaptation

without changing orchestration logic.

---

# Connection Profiles

Azure OpenAI connections are typically declared as named configuration objects.

Example:

```json
{
  "azure_openai": {

    "endpoint": "https://my-openai.openai.azure.com",

    "api_version": "2024-02-01",

    "deployment_name": "gpt-4o",

    "api_key": "{{ SECRET('openai-api-key') }}",

    "temperature": 0.7,

    "max_completion_tokens": 1000
  }
}
```

This creates a reusable named connection profile:

```text
azure_openai
```

---

# Using Connection Names

Nodes do not directly reference Azure endpoints.

Instead, nodes resolve the active connection profile through:

```json
{
  "oai_connection_name": "azure_openai"
}
```

The handler then dynamically resolves:

```python
await cget("oai_connection_name")
```

followed by:

```python
await cget(connection_name)
```

This means orchestration behavior can be redirected entirely through configuration.

---

# Why Named Connections Exist

Named connections separate:
- orchestration structure
- infrastructure configuration
- deployment selection
- inference behavior

This allows flows to remain reusable while infrastructure changes independently.

Example:
- production may use one deployment
- testing may use another
- specific scopes may use cheaper/faster models
- variants may switch providers dynamically

without modifying node code.

---

# Typical Structure

A very common pattern is:

## Upper scope

Define reusable connection profiles:

```json
{
  "azure_openai": {
    "endpoint": "...",
    "deployment_name": "gpt-4o",
    "temperature": 0.7
  },

  "azure_openai_precise": {
    "endpoint": "...",
    "deployment_name": "gpt-4o-mini",
    "temperature": 0.1
  }
}
```

## Lower scope

Select which profile should be used:

```json
{
  "oai_connection_name": "azure_openai_precise"
}
```

This creates scoped deployment specialization without duplicating full connection configuration everywhere.

---

# Scoped Connection Selection

Because `oai_connection_name` uses ordinary scoped config semantics, different parts of the flow may use different Azure deployments automatically.

Example structure:

```text
article_flow/
├── config.json
├── summarize/
│   ├── config.json
│   └── summarize.jinja2
└── creative/
    ├── config.json
    └── brainstorm.jinja2
```

Root config:

```json
{
  "azure_openai": {
    "deployment_name": "gpt-4o",
    "temperature": 0.7
  },

  "azure_openai_precise": {
    "deployment_name": "gpt-4o-mini",
    "temperature": 0.1
  }
}
```

`summarize/config.json`:

```json
{
  "oai_connection_name": "azure_openai_precise"
}
```

`creative/config.json`:

```json
{
  "oai_connection_name": "azure_openai"
}
```

Result:
- summarization nodes use precise low-temperature generation
- creative nodes use more exploratory generation

without modifying node implementations.

---

# Authentication Modes

The Azure integration supports two authentication modes automatically:

| Mode | Behavior |
|---|---|
| API key | uses configured `api_key` |
| Entra ID | uses `DefaultAzureCredential` |

The framework switches automatically based on configuration.

---

# API Key Authentication

If:

```json
{
  "api_key": "..."
}
```

exists in the connection profile, the framework uses API-key authentication.

Example:

```json
{
  "azure_openai": {
    "endpoint": "...",
    "api_version": "...",
    "deployment_name": "...",
    "api_key": "{{ SECRET('openai-api-key') }}"
  }
}
```

This is commonly used for:
- local development
- isolated deployments
- externally managed credentials
- non-Azure execution environments

---

# Entra ID Authentication

If `api_key` is absent, the framework automatically falls back to:

```python
DefaultAzureCredential
```

This enables:
- Managed Identity
- Azure CLI login
- Visual Studio Code login
- environment credentials
- workload identities

without changing orchestration logic.

Example:

```json
{
  "azure_openai": {
    "endpoint": "...",
    "api_version": "...",
    "deployment_name": "gpt-4o"
  }
}
```

No API key is required.

---

# Why This Matters

This creates a very powerful operational property:

The same flow can:
- use API keys locally
- use Managed Identity in Azure
- switch deployments by scope
- switch deployments by variant
- switch deployments by runtime override

without changing node code.

---

# Inference Parameters

Inference behavior is also configuration-driven.

Common parameters include:

| Parameter | Purpose |
|---|---|
| `temperature` | generation randomness |
| `top_p` | token probability sampling |
| `max_completion_tokens` | response length limit |

These values are resolved from the active connection profile.

Example:

```json
{
  "azure_openai": {

    "deployment_name": "gpt-4o",

    "temperature": 0.2,

    "top_p": 0.9,

    "max_completion_tokens": 500
  }
}
```

---

# Default Inference Values

If values are omitted, the framework applies defaults:

| Parameter | Default |
|---|---|
| `temperature` | `1.0` |
| `top_p` | `1.0` |
| `max_completion_tokens` | `800` |

This allows connection profiles to remain lightweight while still supporting specialization where needed.

---

# Scoped Inference Specialization

Inference parameters participate fully in scoped config inheritance.

Example:

Root config:

```json
{
  "azure_openai": {
    "temperature": 0.7
  }
}
```

Nested scope:

```json
{
  "azure_openai": {
    "temperature": 0.1
  }
}
```

Result:
- only that scope becomes more deterministic
- all other connection settings remain inherited

This creates very fine-grained orchestration tuning.

---

# Runtime Overrides

Inference behavior may also be modified dynamically during runtime execution.

Example:

```python
config.override(
    scope="summarization",
    key="azure_openai.temperature",
    value=0.05
)
```

Subsequent generation inside that scope automatically uses the new value.

---

# Client Reuse and Caching

Azure OpenAI clients are cached globally by:
- endpoint
- API version
- authentication mode

This means:
- clients are reused automatically
- repeated flow executions avoid client recreation
- async execution remains efficient
- orchestration overhead stays low

The cache is handled internally by the framework.

---

# Example: Production Structure

Example:

```json
{
  "azure_openai": {

    "endpoint": "https://prod-openai.openai.azure.com",

    "api_version": "2024-02-01",

    "deployment_name": "gpt-4o",

    "temperature": 0.7
  },

  "azure_openai_fast": {

    "endpoint": "https://prod-openai.openai.azure.com",

    "api_version": "2024-02-01",

    "deployment_name": "gpt-4o-mini",

    "temperature": 0.1
  }
}
```

Nested scope:

```json
{
  "oai_connection_name": "azure_openai_fast"
}
```

This allows selective orchestration optimization:
- expensive reasoning where needed
- cheaper/faster execution elsewhere

inside the same flow.

---

# Relationship to the Core Framework

The core framework itself remains provider-agnostic.

Azure support is currently the primary production-ready extension package:

```text
odyss_ai_flows_azure
```

The architecture intentionally separates:
- orchestration semantics
- provider integrations
- infrastructure configuration

This allows additional providers to be added later without redesigning the execution model.

---

# Design Philosophy

The Azure integration intentionally treats:
- deployments
- authentication
- inference behavior
- infrastructure routing

as configuration concerns rather than orchestration concerns.

This allows flows to remain:
- reusable
- environment-independent
- deployment-flexible
- operationally scalable

while still supporting highly specialized runtime behavior through scoped configuration semantics.

The result is a system where:
- orchestration logic
- runtime behavior
- infrastructure configuration

remain cleanly separated without introducing heavy platform abstractions or opaque orchestration layers.