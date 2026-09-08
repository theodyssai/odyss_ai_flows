# Custom Executor

The plugin's executor hierarchy is open. Any class implementing `DurableFlowExecutor` can be passed to `run_durable_flow`.

---

# The Contract

```python
from abc import ABC, abstractmethod
from typing import Any


class DurableFlowExecutor(ABC):

    @abstractmethod
    async def start(
        self,
        flow: Any,
        *,
        inputs: dict[str, Any] | None = None,
        instance_id: str | None = None,
    ) -> str:
        ...
```

`start()` receives the flow argument exactly as passed to `run_durable_flow`, along with optional inputs and instance ID. It returns a string identifying the started orchestration instance.

`flow` can be any type your executor expects: a path string, a flow name, a `DurableFlowPlan`, or a custom object.

---

# Minimal Example

```python
from typing import Any
from odyss_ai_flows_durable import DurableFlowExecutor


class MyCustomExecutor(DurableFlowExecutor):

    def __init__(self, client) -> None:
        self._client = client

    async def start(
        self,
        flow: Any,
        *,
        inputs: dict[str, Any] | None = None,
        instance_id: str | None = None,
    ) -> str:
        return await self._client.start_new(
            "my_custom_orchestrator",
            client_input={"flow": str(flow), "inputs": inputs or {}},
            instance_id=instance_id,
        )
```

Usage is identical to the built-in executors:

```python
executor = MyCustomExecutor(client)
instance_id = await run_durable_flow("flows/my_flow", executor=executor)
```

---

# Reusing Shared Activities

Most custom executors will want to reuse the existing registered activities: node execution, dependency signaling, direct flow dispatch, virtual span construction, and jitter computation.

Use `register_durable_support` to register all shared activities and both standard orchestrators on the blueprint:

```python
from odyss_ai_flows_durable import register_durable_support

register_durable_support(bp, event_client=my_client, retry_options=my_retry)
```

Then register your custom orchestrator on top:

```python
@bp.orchestration_trigger(context_name="context", orchestration="my_custom_orchestrator")
def my_custom_orchestrator(context):
    ...
```

Your executor participates in the same activity pool as the standard executors without duplicating any registrations.

---

# When to Write a Custom Executor

Custom executors are appropriate when:

- the orchestration topology cannot be expressed as a single flow, sequence, or parallel group
- flows need to be dispatched to a different Azure Functions app
- the instance ID scheme requires logic beyond the `instance_id` parameter
- startup requires coordination with an external system before the orchestration begins
- you are integrating with an orchestration platform other than Azure Durable Functions
