from odyss_ai_flows.core.executor.strategy import (
    LeasedConcurrencyStrategy,
)

from odyss_ai_flows.core.runtime.strategy_registry import (
    set_default_strategy_factory,
    clear_default_strategy_factory,
)


class SharedLeaseStrategy(
    LeasedConcurrencyStrategy
):

    def __init__(self):

        super().__init__(
            max_concurrent=1
        )


_SHARED = (
    SharedLeaseStrategy()
)


def install():

    set_default_strategy_factory(
        lambda: _SHARED
    )


def uninstall():

    clear_default_strategy_factory()