# Flow Outputs

Every node in a flow produces a result.

However, the final result exposed by a flow does not necessarily need to contain every internal node output.

The framework distinguishes between:
- internal node results
- exported flow outputs

This allows flows to behave like reusable execution modules with explicitly shaped public outputs rather than exposing their entire internal execution state.

---

# `FlowResult`

`run_flow()` returns a `FlowResult` object.

Example:

```python
from odyss_ai_flows import run_flow
import asyncio


async def main():
    result = await run_flow("example_flow")

    print(result)


asyncio.run(main())
```

`FlowResult` contains:
- execution status
- exported outputs
- all node results
- error information
- serialization helpers

---

# Accessing Outputs

The simplest way to access exported outputs is through dictionary-style access:

```python
summary = result["summary"]
```

This retrieves values from the exported output set.

---

# Default Behavior

By default, if no `outputs.json` file exists, all node results become exported outputs automatically.

This means small flows require no additional configuration.

Example flow:

```text
example_flow/
├── topic.jinja2
├── summary.jinja2
└── keywords.py
```

Without `outputs.json`, all node results are exported automatically:
- `topic`
- `summary`
- `keywords`

---

# `outputs.json`

Flows can define an `outputs.json` file to explicitly control exported outputs.

This file acts as the public output interface of the flow.

It allows:
- filtering outputs
- renaming outputs
- hiding internal nodes
- shaping API responses
- creating reusable orchestration modules

---

# Example: Filtering Outputs

Flow structure:

```text
example_flow/
├── topic.jinja2
├── summary.jinja2
├── internal_cleanup.py
└── outputs.json
```

Contents of `outputs.json`:

```json
{
  "include": [
    "summary"
  ]
}
```

Now only the `summary` node is exported.

Internal nodes remain accessible through debugging APIs but are hidden from the public flow output surface.

---

# Example: Renaming Outputs

`outputs.json` can also rename outputs.

Example:

```json
{
  "include": [
    "summary"
  ],

  "map": {
    "summary": "final_answer"
  }
}
```

Now the exported result becomes:

```python
result["final_answer"]
```

instead of:

```python
result["summary"]
```

This allows flows to expose stable public interfaces even if internal node names change.

---

# Combining Filtering and Mapping

Filtering and mapping can be combined freely.

Example:

```json
{
  "include": [
    "summary",
    "keywords"
  ],

  "map": {
    "summary": "article",
    "keywords": "tags"
  }
}
```

Exported outputs:

```python
result["article"]
result["tags"]
```

while all other node results remain internal.

---

# Accessing All Node Results

Even when outputs are filtered, all node results remain available internally.

Example:

```python
all_results = result.all_node_results
```

This is useful for:
- debugging
- tracing
- observability
- development tooling
- inspecting intermediate execution state

while still exposing a clean public output interface.

---

# Exported Outputs Property

Exported outputs can also be accessed directly:

```python
outputs = result.outputs
```

This returns only the projected/exported output set after `outputs.json` processing.

---

# Outputs as a Collection

`FlowResult` behaves like a read-only mapping over its exported outputs, so you can use it directly wherever a collection is expected:

```python
# Iteration yields exported output names
for name in result:
    print(name)

# Mapping accessors
result.keys()
result.values()
result.items()

# Length and membership
len(result)
"article" in result

# Dictionary conversion
data = dict(result)
```

Every one of these reflects the **projected** output surface — after `include` filtering and `map` renaming. So `result.keys()` returns the mapped, exported names; filtered-out and renamed-away node names are absent:

```json
{
  "include": ["cleanup"],
  "map": { "cleanup": "article" }
}
```

```python
list(result.keys())      # ["article"]
"article" in result      # True
"cleanup" in result      # False  (renamed away)
"draft" in result        # False  (filtered out)
dict(result)             # {"article": "..."}
```

`dict(result)` is a **shallow** conversion: nested `FlowResult` values are preserved as-is. For a fully serializable nested structure, use `to_dict()` instead.

To reach the unfiltered internal graph, use `result.all_node_results` (see above) — the collection protocol intentionally only exposes the public output surface.

---

# Example Full Flow

Flow structure:

```text
article_flow/
├── topic.jinja2
├── draft.jinja2
├── cleanup.py
├── keywords.py
└── outputs.json
```

Contents of `outputs.json`:

```json
{
  "include": [
    "cleanup",
    "keywords"
  ],

  "map": {
    "cleanup": "article",
    "keywords": "tags"
  }
}
```

Running the flow:

```python
from odyss_ai_flows import run_flow
import asyncio


async def main():
    result = await run_flow(
        "article_flow",
        topic="black holes"
    )

    print(result["article"])
    print(result["tags"])


asyncio.run(main())
```

Public outputs remain stable and intentionally shaped even if the internal orchestration evolves later.

---

# Serialization

`FlowResult` supports direct serialization.

Example:

```python
print(result)
```

This automatically produces a JSON-formatted serialized representation.

---

# `to_dict()`

Convert results into a dictionary:

```python
data = result.to_dict()
```

Example structure:

```python
{
    "outputs": {
        "article": "...",
        "tags": [...]
    },

    "status": "SUCCESS",

    "error": None
}
```

---

# `to_json()`

Convert results directly into JSON:

```python
json_data = result.to_json()
```

This is useful for:
- APIs
- persistence
- debugging
- durable execution
- external integrations
- logging pipelines

---

# Safe Serialization

The framework attempts to serialize outputs safely and recursively.

Supported structures include:
- dictionaries
- lists
- tuples
- primitive values
- objects exposing `to_dict()`

Objects that cannot be serialized directly are converted into string representations instead of causing serialization failures.

This behavior helps flows remain robust even when working with mixed runtime object types.

---

# Flow Outputs as Public Interfaces

`outputs.json` is intentionally more than simple filtering configuration.

It defines the public output interface of a flow.

This allows large orchestration systems to:
- evolve internally
- refactor node structures
- add intermediate processing
- introduce debugging nodes
- change execution logic

without breaking external consumers of the flow result.

The result is a cleaner separation between:
- internal orchestration structure
- externally exposed behavior

which becomes increasingly important as flows grow into larger production systems.