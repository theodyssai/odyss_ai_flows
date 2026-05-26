# Dynamic Config Providers

The configuration system supports dynamic runtime value resolution through semantic config providers.

Configuration values are not limited to static JSON literals.

Instead, configuration entries may contain async Jinja-based semantic expressions which are resolved dynamically during runtime access.

Example:

```json
{
  "api_key": "{{ ENV('OPENAI_API_KEY') }}"
}
```

This allows configuration to remain:
- composable
- environment-aware
- secret-aware
- runtime-dynamic
- provider-driven

while still using ordinary JSON configuration files.

---

# Relationship to Scoped Configuration

All configuration inheritance and scoping rules from the previous configuration page still apply.

Semantic providers operate on top of the normal configuration system.

This means:
1. configuration is first merged across scopes
2. semantic providers are then resolved dynamically

Provider semantics therefore work naturally with:
- global configuration
- folder-scoped config
- node-specific config
- nested flow configuration

without changing the underlying configuration model.

---

# Jinja-Based Semantic Rendering

Semantic configuration values use async Jinja rendering internally.

This means providers are called using ordinary Jinja syntax.

Example:

```json
{
  "api_key": "{{ ENV('OPENAI_API_KEY') }}"
}
```

not:

```json
{
  "api_key": "$ENV:OPENAI_API_KEY"
}
```

This approach allows configuration expressions to remain:
- explicit
- composable
- inspectable
- naturally extensible

while reusing familiar Jinja semantics.

---

# Built-In Providers

The framework currently includes several built-in providers:

| Provider | Purpose |
|---|---|
| `ENV(...)` | Environment variable lookup |
| `SECRET(...)` | Secret provider lookup |
| `CONFIG(...)` | External configuration provider lookup |
| `REF(...)` | Config graph reference |
| `LITERAL_SECRET(...)` | Explicit sensitive literal |

---

# Environment Variables

The `ENV()` provider retrieves environment variables.

Example:

```json
{
  "api_key": "{{ ENV('OPENAI_API_KEY') }}"
}
```

This allows configuration to remain environment-independent while avoiding hardcoded secrets inside config files.

---

# Secret Providers

The `SECRET()` provider retrieves secrets through the active secret backend.

Example:

```json
{
  "api_key": "{{ SECRET('openai-api-key') }}"
}
```

The core framework itself remains provider-agnostic.

However, when the Azure extension package is installed:

```text
odyss_ai_flows_azure
```

Azure secret providers automatically register themselves as the default implementation unless a custom provider was already registered.

This means Azure Key Vault integration becomes available automatically without additional bootstrap code.

---

# External Configuration Providers

The `CONFIG()` provider retrieves values from external configuration systems.

Example:

```json
{
  "deployment_name": "{{ CONFIG('azure-openai-deployment') }}"
}
```

Like `SECRET()`, the core framework does not hardcode a specific implementation.

When the Azure extension package is installed, Azure configuration providers automatically become the default implementation unless explicitly overridden.

---

# Config References with `REF()`

`REF()` creates references to other config paths.

Example:

```json
{
  "default_model": "gpt-4o",

  "active_model": "{{ REF('default_model') }}"
}
```

This allows configuration values to reference other parts of the config graph instead of duplicating values.

`REF()` creates semantic references rather than simple text substitution.

Reference traversal is handled later by the configuration system after semantic rendering completes.

---

# Important `REF()` Restriction

`REF()` cannot be mixed with non-reference providers inside the same config entry.

Valid:

```json
{
  "active_model": "{{ REF('default_model') }}"
}
```

Invalid:

```json
{
  "active_model": "{{ REF('default_model') }}-suffix"
}
```

Invalid:

```json
{
  "value": "{{ REF('x') }} {{ ENV('Y') }}"
}
```

This restriction exists intentionally to preserve:
- predictable config graph semantics
- explicit reference behavior
- unambiguous traversal logic

`REF()` is treated as a structural config reference rather than a string templating helper.

---

# Sensitive Values

Some providers are marked as sensitive.

Examples:
- `SECRET()`
- `LITERAL_SECRET()`

Sensitive values are automatically wrapped as `SensitiveValue` objects after rendering.

This helps prevent accidental disclosure through:
- logs
- debugging output
- serialization
- traces
- prompt inspection

Example:

```python
value = await cget("api_key")

print(value)
```

Output:

```text
<SensitiveValue>
```

---

# Explicit Secret Access

Sensitive values can still be accessed explicitly when required.

Example:

```python
real_value = (
    await cget("api_key")
).unwrap()
```

The explicit `.unwrap()` call makes sensitive access intentional and visible inside code.

---

# Explicit Sensitive Literals

`LITERAL_SECRET()` allows explicitly marking hardcoded values as sensitive.

Example:

```json
{
  "api_key": "{{ LITERAL_SECRET('hardcoded-secret') }}"
}
```

This is useful when:
- temporary secrets are needed
- migration is incomplete
- local development requires explicit literals

while still preserving safe logging behavior.

---

# Async Resolution

Configuration providers may execute asynchronously.

This is one of the reasons `cget()` is asynchronous.

Providers may involve:
- environment access
- external secret systems
- external configuration systems
- network calls
- semantic rendering
- recursive config traversal

The async API allows the configuration system to scale naturally into more advanced runtime behavior without changing the user-facing configuration model.

---

# Lazy Resolution

Semantic config values are resolved lazily.

This means providers execute only when the corresponding config value is actually requested through `cget()`.

Example:

```python
deployment = await cget(
    "azure_openai.deployment_name"
)
```

If the value is never accessed, the provider is never executed.

This keeps configuration lightweight for flows that only use small portions of large config trees.

---

# Semantic Caching

Resolved semantic expressions are cached automatically during runtime execution.

This reduces repeated provider execution overhead for frequently accessed config entries.

Caching is handled automatically by the framework and requires no manual configuration for ordinary usage.

---

# Example Full Configuration

Example:

```json
{
  "azure_openai": {
    "deployment_name": "{{ CONFIG('azure-openai-deployment') }}",

    "api_key": "{{ SECRET('openai-api-key') }}",

    "temperature": 0.7
  },

  "defaults": {
    "model": "gpt-4o"
  },

  "active_model": "{{ REF('defaults.model') }}"
}
```

Usage inside a node:

```python
from odyss_ai_flows import *


@node
async def summarize():

    deployment = await cget(
        "azure_openai.deployment_name"
    )

    api_key = (
        await cget(
            "azure_openai.api_key"
        )
    ).unwrap()

    model = await cget(
        "active_model"
    )

    return {
        "deployment": deployment,
        "model": model,
        "api_key_length": len(api_key)
    }
```

---

# Provider-Agnostic Core

The core framework intentionally does not hardcode Azure-specific infrastructure behavior.

Instead:
- providers are modular
- integrations are optional
- defaults self-bootstrap when extensions are installed
- custom implementations may override defaults

This allows the framework to remain:
- lightweight
- extensible
- provider-agnostic

while still providing extremely low setup overhead for common Azure-based deployments.

---

# Design Philosophy

The configuration system intentionally treats configuration as:
- runtime-aware
- semantically composable
- async-capable
- execution-integrated

rather than simple static JSON loading.

At the same time, the system attempts to remain:
- explicit
- inspectable
- predictable
- incrementally adoptable

Small flows may ignore providers entirely and use only static JSON.

Larger systems can gradually adopt:
- environment resolution
- secret systems
- external config providers
- semantic references

without changing orchestration logic or execution structure.