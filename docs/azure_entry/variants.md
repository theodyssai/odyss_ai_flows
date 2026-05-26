# Variants and Rebased Flow Trees

The framework supports variants: additional filesystem trees that are rebased onto a base flow structure during repository construction.

Variants allow flows to be specialized without modifying the original flow itself.

This makes it possible to create:
- deployment-specific behavior
- experimental orchestration versions
- customer-specific overlays
- feature variants
- environment-specific execution
- reusable flow modifications

without introducing large amounts of conditional orchestration logic.

---

# Core Idea

Variants are not runtime condition branches.

Instead, they are:
- additional filesystem trees
- scanned independently
- rebased onto the main flow namespace
- merged into the same runtime repository

Conceptually:

```text
base flow
    +
variant overlay
    ↓
single merged runtime repository
```

The resulting flow behaves as if the variant files physically existed inside the base flow.

---

# Basic Example

Base flow:

```text
flows/article_flow/
├── summarize.jinja2
├── classify.jinja2
└── config.json
```

Variant:

```text
variants/fast/
├── summarize.jinja2
└── config.json
```

Execution:

```python
await run_flow(
    "flows/article_flow",

    variant_paths=[
        "variants/fast"
    ]
)
```

The variant files become rebased onto the base flow structure during repository construction.

---

# Rebased Paths

Rebased paths are one of the most important concepts in the variant system.

Variant files do not preserve their physical filesystem paths.

Instead, they are projected into the namespace of the base flow.

Example:

Physical variant file:

```text
variants/fast/summarize.jinja2
```

Rebased runtime path:

```text
flows/article_flow/summarize.jinja2
```

This rebased path becomes the semantic identity of the file during flow execution.

---

# Why Rebasing Exists

Rebasing allows variants to behave like overlays rather than separate flows.

This means:
- existing node names remain stable
- node scopes remain stable
- dependency resolution remains stable
- config scoping remains stable

while allowing parts of the flow to be replaced or extended.

Without rebasing, variants would behave like unrelated independent flows rather than composable overlays.

---

# Node Scope and Rebasing

Node scope is derived from the rebased runtime path rather than the physical variant path.

This is extremely important.

Example:

Physical variant file:

```text
variants/fast/summarize.jinja2
```

Rebased runtime path:

```text
flows/article_flow/summarize.jinja2
```

Effective node scope:

```text
flows/article_flow/summarize
```

This means variants preserve:
- node identity
- dependency structure
- config scoping semantics

even though the physical files may exist elsewhere.

---

# Variant Override Behavior

Most file types override earlier files with the same rebased path.

Example:

Base flow:

```text
flows/article_flow/summarize.jinja2
```

Variant:

```text
variants/fast/summarize.jinja2
```

Result:
- the variant version replaces the base node

The framework treats this as an intentional override.

---

# Config Files Behave Differently

Config files do not override each other.

They merge.

This is one of the most important behaviors of the variant system.

Example:

Base config:

```json
{
  "azure_openai": {
    "temperature": 0.7,
    "max_tokens": 1000
  }
}
```

Variant config:

```json
{
  "azure_openai": {
    "temperature": 0.2
  }
}
```

Effective runtime config:

```json
{
  "temperature": 0.2,
  "max_tokens": 1000
}
```

This allows variants to specialize configuration without duplicating entire config trees.

---

# Folder Config Rebasing

Folder configs represent semantic scopes rather than physical files.

Example:

```text
config.json
```

does not represent:
```text
.../config.json
```

semantically.

Instead, it represents:
```text
the folder scope itself
```

This allows config scoping to remain stable across rebased variant trees.

---

# Node Config Rebasing

Node config files behave similarly.

Example:

```text
summarize.config.json
```

represents configuration attached to:

```text
summarize
```

node scope rather than the config file itself.

This preserves correct node-local config behavior under rebasing.

---

# Multiple Variants

Multiple variants may be chained together.

Example:

```python
await run_flow(

    "flows/article_flow",

    variant_paths=[
        "variants/fast",
        "variants/customer_a",
        "variants/debug"
    ]
)
```

Variants are applied sequentially in the order provided.

Later variants override earlier variants when rebased paths collide.

---

# Variant Chaining Example

Base flow:

```text
flows/article_flow/
└── summarize.jinja2
```

Variant 1:

```text
variants/fast/
└── summarize.jinja2
```

Variant 2:

```text
variants/customer_a/
└── summarize.jinja2
```

Result:
- `customer_a` version wins
- because it was applied later

This creates deterministic layering behavior.

---

# Config Merge Across Multiple Variants

Config merging also chains progressively.

Example:

Base:

```json
{
  "azure_openai": {
    "temperature": 0.7,
    "max_tokens": 1000
  }
}
```

Variant A:

```json
{
  "azure_openai": {
    "temperature": 0.4
  }
}
```

Variant B:

```json
{
  "azure_openai": {
    "max_tokens": 300
  }
}
```

Final result:

```json
{
  "temperature": 0.4,
  "max_tokens": 300
}
```

This creates composable configuration specialization layers.

---

# Variants Affect All File Types

Variants apply to all repository-managed file kinds.

This includes:
- Jinja nodes
- Python nodes
- config files
- model files
- outputs.json
- future custom file types

The variant system operates at the repository layer rather than being limited to node execution only.

---

# outputs.json Behavior

`outputs.json` behaves like ordinary files and therefore overrides rather than merges.

Example:

```text
base/outputs.json
variant/outputs.json
```

The variant version replaces the base version entirely.

This differs intentionally from config merging semantics.

---

# Why Variants Exist

Variants solve a very important orchestration problem:

How can flows be specialized without:
- duplicating entire flows
- introducing conditional orchestration logic
- creating large branching execution trees
- maintaining many nearly-identical flow copies

Variants provide a filesystem-composition-based answer to this problem.

---

# Practical Use Cases

Typical variant use cases include:
- production vs development orchestration
- customer-specific customization
- fast vs high-quality generation pipelines
- provider-specific execution behavior
- A/B orchestration experimentation
- temporary feature overlays
- deployment-specific tuning
- debugging instrumentation
- reusable orchestration modifications

---

# Example: Fast vs Quality Variant

Base flow:

```text
article_flow/
├── summarize.jinja2
├── summarize.config.json
└── classify.jinja2
```

Fast variant:

```text
variants/fast/
└── summarize.config.json
```

Fast variant config:

```json
{
  "azure_openai": {
    "temperature": 0.1,
    "max_tokens": 200
  }
}
```

Execution:

```python
await run_flow(
    "article_flow",
    variant_paths=[
        "variants/fast"
    ]
)
```

The orchestration structure remains identical while generation behavior changes.

---

# Relationship to Repository Architecture

Variants operate at the repository layer.

This means they participate in:
- file discovery
- node construction
- config scoping
- outputs resolution
- runtime repository semantics

before flow execution begins.

The executor itself does not need special variant logic because the repository already represents the fully merged runtime view.

---

# Relationship to Virtual and Hybrid Flows

Variants are part of the broader repository abstraction system.

The repository layer can combine:
- physical filesystem files
- rebased variants
- virtual files
- prepared flow overlays

into a single runtime repository representation.

Virtual and hybrid flows are covered separately in dedicated documentation.

---

# Design Philosophy

Variants intentionally treat orchestration structure as:
- composable
- layered
- filesystem-driven
- repository-native

rather than relying on:
- runtime branching logic
- profile condition systems
- orchestration flags
- deeply nested execution conditionals

The goal is allowing orchestration systems to evolve through composition and overlays rather than through increasingly complex runtime decision trees.

This keeps flows:
- modular
- inspectable
- deterministic
- reusable
- operationally understandable

even as specialization complexity grows.