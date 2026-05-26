# Flow Inputs

Flow inputs are external runtime values passed into a flow execution.

They represent data coming from outside the flow itself:
- user requests
- API payloads
- runtime parameters
- execution metadata
- secrets
- orchestration values
- external context

Inputs are accessed through `iget()`.

---

# `iget()` vs `nget()`

The framework intentionally separates:
- runtime inputs
- node dependencies

These are different concepts.

Use:
- `iget()` for values provided from outside the flow
- `nget()` for retrieving results of other nodes

Example:

```python
topic = iget("topic")

summary = await nget("summary_node")
```

This distinction keeps flows easier to reason about:
- `iget()` accesses external runtime state
- `nget()` synchronizes with internal node execution

Unlike `nget()`, `iget()` is not asynchronous because inputs are already available locally within the current flow run.

---

# Passing Inputs to `run_flow()`

Inputs can be passed into a flow in two ways:
- through the `inputs` dictionary
- as keyword arguments

Example using `inputs`:

```python
from odyss_ai_flows import run_flow
import asyncio


async def main():
    result = await run_flow(
        "example_flow",
        inputs={
            "topic": "black holes",
            "style": "scientific"
        }
    )

    print(result)


asyncio.run(main())
```

Example using keyword arguments:

```python
from odyss_ai_flows import run_flow
import asyncio


async def main():
    result = await run_flow(
        "example_flow",
        topic="black holes",
        style="scientific"
    )

    print(result)


asyncio.run(main())
```

Both approaches are merged into the same runtime input repository.

Keyword arguments override duplicate keys from the `inputs` dictionary.

---

# Using `iget()` in Python Nodes

Python nodes access inputs directly through `iget()`.

Example:

```python
from odyss_ai_flows import *


@node
async def build_prompt():
    topic = iget("topic")

    return f"Explain {topic} in simple terms."
```

Inputs are immediately available and do not require `await`.

---

# Using Defaults

`iget()` supports default values.

Example:

```python
style = iget("style", default="neutral")
```

If the input does not exist, the default value is returned instead.

This makes optional runtime inputs easy to support without excessive boilerplate.

---

# Multiple Inputs

`iget()` can also retrieve multiple inputs at once.

Example:

```python
topic, style = iget(
    ["topic", "style"],
    default=["space", "neutral"]
)
```

This is primarily a convenience feature for compact orchestration logic.

---

# Using `iget()` in Jinja Nodes

Inside Jinja nodes, `iget()` is automatically injected into the template context.

No imports are required.

Example:

```jinja2
Write a short article about:

{{ iget("topic") }}
```

Defaults work the same way:

```jinja2
Style:

{{ iget("style", default="neutral") }}
```

Like in Python nodes, `iget()` is synchronous and does not use `await`.

---

# Example: Flow Using Inputs

Flow structure:

```text
example_flow/
├── prompt.jinja2
├── process.py
└── summary.jinja2
```

Contents of `prompt.jinja2`:

```jinja2
Write a short explanation about:

{{ iget("topic") }}

Use style:

{{ iget("style", default="neutral") }}
```

Contents of `process.py`:

```python
from odyss_ai_flows import *


@node
async def process():
    user_name = iget("user_name", default="anonymous")

    prompt = await nget("prompt")

    return f"Request created by {user_name}:\n\n{prompt}"
```

Contents of `summary.jinja2`:

```jinja2
Summarize this request:

{{ nget("process") }}
```

Running the flow:

```python
from odyss_ai_flows import run_flow
import asyncio


async def main():
    result = await run_flow(
        "example_flow",
        topic="quantum mechanics",
        user_name="Alek"
    )

    print(result)


asyncio.run(main())
```

---

# Sensitive Inputs

Flows often require sensitive runtime values such as:
- API keys
- access tokens
- credentials
- private user data
- internal identifiers

The framework supports marking selected inputs as sensitive.

Sensitive inputs are automatically wrapped to reduce accidental exposure through:
- logs
- traces
- debugging output
- serialization
- prompt inspection
- monitoring systems

---

# Configuring Sensitive Inputs

Sensitive input keys are configured through scoped configuration:

```json
{
  "inputs": {
    "sensitive_keys": [
      "api_key",
      "password",
      "token"
    ]
  }
}
```

Any matching runtime input is automatically wrapped as a `SensitiveValue`.

---

# Sensitive Value Behavior

Sensitive values intentionally hide their real contents when displayed.

Example:

```python
secret = iget("api_key")

print(secret)
```

Output:

```text
<SensitiveValue>
```

This helps prevent accidental secret leakage during debugging or observability collection.

---

# Accessing the Real Value

Sensitive values can still be accessed explicitly when required.

Example:

```python
real_key = iget("api_key").unwrap()
```

The explicit `.unwrap()` call makes sensitive access intentional and visible in code.

---

# Input Scope and Isolation

Inputs are scoped to the current flow run.

This means:
- concurrent flows do not share inputs
- nested flows may receive independent inputs
- runtime state remains isolated between executions

Inputs therefore behave like execution-local runtime state rather than global mutable variables.

---

# Design Philosophy

The framework intentionally separates:
- runtime inputs (`iget`)
- node dependencies (`nget`)
- configuration (`cget`)

This creates a clearer execution model where:
- external runtime state
- internal orchestration state
- configuration state

remain conceptually distinct.

The result is lower orchestration complexity and more readable flow logic as systems scale.