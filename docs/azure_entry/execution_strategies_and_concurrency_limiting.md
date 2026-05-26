# Execution Strategies and Concurrency

The framework supports configurable execution strategies that control how node work is admitted and coordinated during runtime execution.

By default, flows execute fully asynchronously without additional orchestration throttling.

However, larger systems often require:
- limiting concurrent node execution
- reducing pressure on external APIs
- controlling resource usage
- preventing orchestration overload
- coordinating nested flow execution
- introducing execution backpressure

Execution strategies exist to solve these problems without changing flow logic itself.

---

# Default Execution Behavior

By default, flows execute using the standard execution strategy:

```python
DefaultWorkStrategy
```

This means:
- nodes execute asynchronously
- no explicit concurrency throttling is applied
- orchestration remains naturally concurrent
- nested flows inherit the same behavior

For many small or moderate flows, this is completely sufficient.

---

# Why Concurrency Control Matters

AI orchestration systems often interact with:
- LLM APIs
- databases
- search systems
- external services
- nested orchestration
- long-running tasks

Without concurrency control, large orchestration graphs may:
- overload external systems
- exceed API limits
- create unnecessary contention
- generate excessive parallelism
- consume too many runtime resources

Execution strategies provide a lightweight policy layer for controlling orchestration pressure.

---

# Simple Concurrency Limiting

The simplest way to limit concurrency is:

```python
max_concurrency=
```

Example:

```python
from odyss_ai_flows import run_flow
import asyncio


async def main():

    result = await run_flow(
        "article_flow",
        max_concurrency=4
    )

    print(result)


asyncio.run(main())
```

This creates a leased concurrency strategy internally with a maximum of four concurrently active execution leases.

---

# What `max_concurrency` Actually Limits

`max_concurrency` does not simply limit:
- created asyncio tasks
- coroutine count
- background awaits

Instead, it limits:
- actively leased node execution

This distinction is important.

The goal is limiting meaningful orchestration work rather than preventing async execution entirely.

---

# Leased Concurrency

The built-in concurrency system uses:

```python
LeasedConcurrencyStrategy
```

Internally, nodes acquire execution leases before running.

Conceptually:

```text
node begins execution
    ↓
lease acquired
    ↓
node executes
    ↓
lease released
```

This creates controlled orchestration pressure while still preserving fully async execution behavior.

---

# Nested Flow Execution and Lease Yielding

One of the most important behaviors of the leased strategy is temporary lease yielding during blocked orchestration waits.

Without lease yielding, a blocked node would continue occupying concurrency capacity while waiting for nested orchestration.

The leased strategy instead allows execution capacity to be temporarily released during certain orchestration waits.

Conceptually:

```text
node starts
    ↓
lease acquired
    ↓
node awaits nested flow
    ↓
lease temporarily released
    ↓
other orchestration work proceeds
    ↓
lease reacquired before continuing
```

This significantly improves orchestration throughput in systems using:
- nested flows
- reusable subflows
- orchestration fan-out
- blocking waits
- concurrent orchestration trees

without requiring users to manually coordinate semaphore behavior.

---

# Example: Nested Flow Execution

Example:

```python
from odyss_ai_flows import *


@node
async def generate_article():

    result = await run_flow(
        "summarization_flow"
    )

    return result["summary"]
```

Under leased concurrency:
- the parent node may temporarily yield its execution lease while awaiting the nested flow
- other nodes may continue progressing
- orchestration throughput remains efficient even under strict concurrency limits

---

# Explicit Strategy Objects

Advanced users may provide strategy objects directly.

Example:

```python
from odyss_ai_flows import run_flow

from odyss_ai_flows.core.executor.strategy import (
    LeasedConcurrencyStrategy,
)

import asyncio


async def main():

    strategy = (
        LeasedConcurrencyStrategy(4)
    )

    result = await run_flow(
        "article_flow",
        strategy=strategy
    )

    print(result)


asyncio.run(main())
```

This allows more explicit execution policy control.

---

# `strategy` vs `max_concurrency`

These parameters are mutually exclusive.

Invalid:

```python
await run_flow(
    "article_flow",
    strategy=my_strategy,
    max_concurrency=4
)
```

The framework intentionally prevents ambiguous execution policy configuration.

---

# Strategy Inheritance in Nested Flows

Nested flows automatically inherit the parent executor strategy unless explicitly overridden.

Example:

```python
await run_flow(
    "top_level_flow",
    max_concurrency=4
)
```

If a node later executes:

```python
await run_flow(
    "nested_flow"
)
```

the nested flow automatically inherits the same execution strategy.

This preserves:
- orchestration consistency
- predictable concurrency behavior
- shared execution policy
- nested orchestration coordination

without requiring explicit propagation code.

---

# Global Default Strategies

Applications may configure a global default strategy factory.

Example:

```python
from odyss_ai_flows.core.runtime.strategy_registry import (
    set_default_strategy_factory,
)

from odyss_ai_flows.core.executor.strategy import (
    LeasedConcurrencyStrategy,
)


set_default_strategy_factory(

    lambda:
        LeasedConcurrencyStrategy(4)
)
```

All top-level flow executions will then use that strategy automatically unless explicitly overridden.

---

# Strategy Factory Semantics

The global strategy system uses factories rather than static strategy objects.

This means the factory executes separately for each flow execution.

Example:

```python
lambda: LeasedConcurrencyStrategy(4)
```

creates a fresh strategy instance for every top-level flow run.

---

# Shared Strategy Pools

Advanced users may intentionally share strategy instances across multiple flow executions.

Example:

```python
shared_strategy = (
    LeasedConcurrencyStrategy(4)
)

set_default_strategy_factory(
    lambda: shared_strategy
)
```

This creates a shared global concurrency pool across multiple top-level flow executions.

This can be useful when multiple independent flows should collectively obey the same orchestration pressure limits.

---

# Strategy Resolution Order

Execution strategy resolution follows this order:

```text
explicit strategy
    ↓
max_concurrency shortcut
    ↓
parent flow strategy inheritance
    ↓
global default strategy factory
    ↓
DefaultWorkStrategy
```

This keeps strategy behavior predictable while allowing local overrides where necessary.

---

# Example: Shared Global Concurrency

Example:

```python
import asyncio

from odyss_ai_flows import run_flow

from odyss_ai_flows.core.runtime.strategy_registry import (
    set_default_strategy_factory,
)

from odyss_ai_flows.core.executor.strategy import (
    LeasedConcurrencyStrategy,
)


shared_strategy = (
    LeasedConcurrencyStrategy(2)
)

set_default_strategy_factory(
    lambda: shared_strategy
)


async def main():

    await asyncio.gather(

        run_flow("flow_a"),

        run_flow("flow_b"),

        run_flow("flow_c"),
    )


asyncio.run(main())
```

In this scenario:
- all three flows share the same concurrency pool
- at most two leased node executions remain active simultaneously
- nested orchestration still remains fully functional

---

# Relationship to Async Execution

Execution strategies do not replace asyncio.

The framework remains:
- fully async
- task-based
- non-blocking
- coroutine-driven

Strategies simply introduce orchestration policy on top of async execution behavior.

---

# Typical Usage

Most users should begin with:

```python
max_concurrency=
```

This provides a simple and practical orchestration pressure control mechanism without requiring custom strategy implementations.

Explicit strategies become more useful in:
- large orchestration systems
- reusable runtime environments
- shared concurrency pools
- custom orchestration policies
- advanced runtime coordination

---

# Design Philosophy

Execution strategies intentionally separate:
- orchestration logic
- concurrency policy
- execution pressure management

This allows flows to remain:
- composable
- reusable
- async-native
- orchestration-focused

without embedding concurrency management directly into node logic.

The framework attempts to provide:
- natural async execution
- lightweight orchestration control
- nested execution coordination
- execution pressure management

without forcing users into heavyweight scheduling infrastructure or opaque orchestration runtimes.