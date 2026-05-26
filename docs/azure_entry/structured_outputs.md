# Structured Outputs with `.model.py`

The framework supports structured LLM outputs through optional:

```text
<node_name>.model.py
```

files.

Structured outputs are treated as:
- an execution specialization of ordinary LLM nodes
- not a separate orchestration system
- not a separate node type
- not a separate runtime

This allows structured and non-structured generation to coexist naturally inside the same orchestration model.

---

# The Core Idea

Example:

```text
summarize.jinja2
summarize.model.py
```

The `.model.py` file automatically augments the node:
- same node
- same orchestration semantics
- same dependencies
- same execution model

but with structured output parsing enabled.

---

# Why This Exists

Many LLM workflows require:
- JSON extraction
- typed outputs
- structured metadata
- deterministic parsing
- nested schemas
- validation

The framework therefore allows nodes to declare:
- expected structured output models
- directly next to the node itself

without introducing:
- separate orchestration primitives
- special structured node types
- separate runtime systems

---

# Model File Discovery

The framework automatically discovers model files through naming convention.

Example:

```text
article_summary/
├── summarize.jinja2
└── summarize.model.py
```

The model file is automatically associated with:

```text
summarize
```

node.

No explicit registration is required.

---

# Required Model Declaration

A `.model.py` file must contain at least one class decorated with:

```python
@model
```

Example:

```python
from odyss_ai_flows import *

from pydantic import BaseModel


@model
class SummaryResult(BaseModel):

    summary: str

    confidence: float
```

The framework scans the module and automatically discovers the decorated class.

---

# Why `@model` Exists

The framework intentionally does not assume:
- first class in file
- specific class names
- implicit conventions

Instead:
- `@model`
- explicitly marks the intended structured output model

This keeps model discovery deterministic and extensible.

---

# Full Example

## Node

```text
summarize.jinja2
```

```jinja2
Summarize this article:

{{ iget("article") }}

Return:
- concise summary
- confidence score
```

---

## Structured Model

```text
summarize.model.py
```

```python
from odyss_ai_flows import *

from pydantic import BaseModel


@model
class SummaryResult(BaseModel):

    summary: str

    confidence: float
```

---

## Execution

```python
result = await run_flow(
    "article_flow",
    article="Black holes are..."
)

print(result["summarize"].summary)
print(result["summarize"].confidence)
```

---

# Automatic Structured Execution

The presence of:

```text
summarize.model.py
```

automatically enables structured execution mode.

The node itself does not change.

Instead:
- the handler receives `model_class`
- the pipeline adapts automatically
- the provider caller switches into structured mode

This behavior is fully automatic.

---

# Core vs Plugin Responsibilities

The structured output system is intentionally split between:
- core framework responsibilities
- provider/plugin responsibilities

This separation is extremely important architecturally.

---

# Core Framework Responsibilities

The core framework:
- discovers `.model.py`
- loads the model module
- finds the `@model` class
- injects `model_class` into handler state
- preserves orchestration semantics

The core itself does not:
- parse provider responses
- enforce provider APIs
- implement provider-specific structured execution

---

# Provider Responsibilities

Provider plugins decide:
- how structured outputs are requested
- how provider parsing works
- how validation occurs
- how provider-specific APIs are used

Example Azure behavior:

```python
await client.beta.chat.completions.parse(
    model=deployment,
    messages=messages,
    response_format=model_cls,
)
```

This is implemented entirely by the Azure plugin rather than the core framework.

---

# Automatic Structured Mode

The Azure caller automatically adapts based on whether:

```python
self.handler.model_class
```

exists.

## No model

→ ordinary text generation

## Model present

→ structured parsing mode

This means the same node can transparently switch between:
- text mode
- structured mode

without changing orchestration semantics.

---

# Structured Outputs Are Pipeline-Native

Structured execution is part of the pipeline system.

Typical flow:

```text
render
    ↓
load model_class
    ↓
build messages
    ↓
structured provider call
    ↓
parsed Pydantic object
```

This keeps structured outputs:
- composable
- provider-aware
- execution-native

rather than being implemented as a separate orchestration layer.

---

# Nested Pydantic Models

Nested Pydantic structures are fully supported.

Example:

```python
from odyss_ai_flows import *

from pydantic import BaseModel


class Author(BaseModel):

    name: str

    expertise: str


@model
class ArticleAnalysis(BaseModel):

    title: str

    summary: str

    author: Author

    tags: list[str]
```

The framework preserves the full Pydantic model structure.

---

# Structured Validation

The provider integration attempts to parse the LLM response into the declared model.

If parsing fails:
- provider parsing raises
- node execution fails normally
- flow orchestration semantics remain unchanged

Structured parsing therefore behaves like ordinary execution semantics rather than special orchestration logic.

---

# Relationship to `{{ model(...) }}`

The framework also supports runtime model injection through:

```jinja2
{{ model(MyModel) }}
```

This differs from `.model.py`.

---

## `.model.py`

Static repository-level model attachment.

Best for:
- stable node contracts
- reusable flows
- filesystem-defined orchestration

---

## `{{ model(...) }}`

Dynamic runtime model attachment.

Best for:
- adaptive orchestration
- runtime-generated schemas
- action systems
- dynamic execution

---

# Relationship to Variants

Because `.model.py` files are repository-managed files:
- variants may override them
- virtual flows may inject them
- hybrid flows may generate them

Example:

```text
summarize.model.py
```

may differ between:
- production variant
- lightweight variant
- extraction variant

without changing orchestration structure.

---

# Relationship to Virtual and Hybrid Flows

Virtual and hybrid flows may inject model files dynamically through:

```python
flow.fset(
    "summarize.model.py",
    model_callable_or_path
)
```

This allows:
- runtime-generated schemas
- dynamic structured orchestration
- generated extraction systems

inside ordinary repository semantics.

---

# Provider Compatibility

The core framework supports structured output semantics independently of provider implementation.

Actual structured execution depends on:
- active provider plugin
- selected caller component
- underlying model capabilities

Different providers may implement:
- parsing
- schema enforcement
- validation
- generation semantics

differently.

---

# Current Azure Behavior

The Azure extension currently uses:
- Azure OpenAI structured parsing APIs
- Pydantic-compatible response parsing
- automatic typed object reconstruction

This allows nodes to return fully typed Python objects directly from LLM execution.

---

# Example: Typed Extraction Flow

Example:

```jinja2
Extract:
- title
- author
- sentiment
- key entities

from this article:

{{ iget("article") }}
```

Model:

```python
from odyss_ai_flows import *

from pydantic import BaseModel


class Entity(BaseModel):

    name: str

    type: str


@model
class ArticleExtraction(BaseModel):

    title: str

    author: str

    sentiment: str

    entities: list[Entity]
```

Result:

```python
result["extract"].entities[0].name
```

returns ordinary typed Python objects.

---

# Design Philosophy

The framework intentionally treats structured outputs as:
- execution specialization
- provider adaptation
- pipeline behavior

rather than:
- separate orchestration primitives
- special node systems
- isolated runtimes

This keeps structured execution:
- composable
- explicit
- repository-native
- provider-extensible

while preserving the same orchestration semantics used for ordinary text generation.

The result is a system where:
- text outputs
- structured outputs
- multimodal outputs
- action outputs

all remain part of the same unified orchestration architecture.