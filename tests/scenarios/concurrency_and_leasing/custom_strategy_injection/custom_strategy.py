from __future__ import annotations

from typing import Any
from typing import Awaitable
from typing import Callable

from odyss_ai_flows.core.executor.strategy import (
    WorkStrategy,
)

from tests.scenarios.concurrency_and_leasing.custom_strategy_injection.shared import (
    record,
)


class RecordingStrategy(
    WorkStrategy
):

    async def run_node(

        self,
        name: str,
        coro_fn: Callable[
            [],
            Awaitable[Any],
        ],
    ) -> Any:

        await record(
            f"run:{name}:start"
        )

        result = await coro_fn()

        await record(
            f"run:{name}:end"
        )

        return result

    async def await_with_policy(

        self,
        awaitable,
    ):

        await record(
            "await:start"
        )

        result = await awaitable

        await record(
            "await:end"
        )

        return result