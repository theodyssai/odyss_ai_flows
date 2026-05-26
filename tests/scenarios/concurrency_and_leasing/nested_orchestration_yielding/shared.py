import asyncio

from odyss_ai_flows.core.executor.strategy import (
    LeasePool,
    LeasedConcurrencyStrategy,
)

from odyss_ai_flows.core.runtime.strategy_registry import (
    set_default_strategy_factory,
    clear_default_strategy_factory,
)

from odyss_ai_flows.core.utils.logger import (
    logger,
)


EVENTS = []

CURRENT_ACTIVE = 0
MAX_ACTIVE = 0


async def reset():

    global CURRENT_ACTIVE
    global MAX_ACTIVE

    EVENTS.clear()

    CURRENT_ACTIVE = 0
    MAX_ACTIVE = 0

    logger.info(
        "[scenario] reset"
    )


class InstrumentedLeasePool(
    LeasePool
):

    async def acquire(
        self,
    ) -> None:

        global CURRENT_ACTIVE
        global MAX_ACTIVE

        await super().acquire()

        CURRENT_ACTIVE += 1

        if CURRENT_ACTIVE > MAX_ACTIVE:

            MAX_ACTIVE = CURRENT_ACTIVE

        EVENTS.append(
            "acquire"
        )

        logger.info(
            "[scenario] acquire | current=%s | max=%s",
            CURRENT_ACTIVE,
            MAX_ACTIVE,
        )

    def release(
        self,
    ) -> None:

        global CURRENT_ACTIVE

        CURRENT_ACTIVE -= 1

        EVENTS.append(
            "release"
        )

        logger.info(
            "[scenario] release | current=%s",
            CURRENT_ACTIVE,
        )

        super().release()


class InstrumentedStrategy(
    LeasedConcurrencyStrategy
):

    def __init__(
        self,
        max_concurrent: int,
    ):

        logger.info(
            "[scenario] strategy init | limit=%s",
            max_concurrent,
        )

        self._lease_pool = (
            InstrumentedLeasePool(
                max_concurrent
            )
        )

    async def await_with_policy(
        self,
        awaitable,
    ):

        if not self._lease_pool.has_lease():

            return await awaitable

        logger.info(
            "[scenario] yielding lease"
        )

        self._lease_pool.release()

        try:

            return await awaitable

        finally:

            await self._lease_pool.ensure_acquired()

            EVENTS.append(
                "reacquire"
            )

            logger.info(
                "[scenario] reacquire | current=%s",
                CURRENT_ACTIVE,
            )


_SHARED = (
    InstrumentedStrategy(
        max_concurrent=2
    )
)


def install():

    logger.info(
        "[scenario] install"
    )

    set_default_strategy_factory(
        lambda: _SHARED
    )


def uninstall():

    logger.info(
        "[scenario] uninstall"
    )

    clear_default_strategy_factory()