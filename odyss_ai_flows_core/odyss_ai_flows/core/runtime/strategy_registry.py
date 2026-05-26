# Copyright 2026 ODYSS.AI AG
# SPDX-License-Identifier: Apache-2.0
#
# See the NOTICE file for attribution information.
#
# Author:
# Aleksander Bydłowski
# abydlowski@theodyss.ai
# aleksander.bydlowski@gmail.com
from __future__ import annotations

from typing import Callable, Optional

from odyss_ai_flows.core.executor.strategy import (
    WorkStrategy,
)

# ---------------------------------------------------------
# Global default strategy factory
# ---------------------------------------------------------

DEFAULT_STRATEGY_FACTORY: Optional[
    Callable[[], WorkStrategy]
] = None


# ---------------------------------------------------------
# Public API
# ---------------------------------------------------------

def set_default_strategy_factory(
    factory: Callable[[], WorkStrategy],
) -> None:
    """
    Set the global default strategy factory.

    The factory is invoked separately for each flow execution.

    Example:
        set_default_strategy_factory(
            lambda: LeasedConcurrencyStrategy(4)
        )
    """

    global DEFAULT_STRATEGY_FACTORY

    if not callable(factory):
        raise TypeError(
            "strategy factory must be callable"
        )

    DEFAULT_STRATEGY_FACTORY = factory


def clear_default_strategy_factory() -> None:
    """
    Remove the global default strategy factory.
    """

    global DEFAULT_STRATEGY_FACTORY

    DEFAULT_STRATEGY_FACTORY = None


def get_default_strategy_factory() -> Optional[
    Callable[[], WorkStrategy]
]:
    """
    Return the currently configured global
    default strategy factory.
    """

    return DEFAULT_STRATEGY_FACTORY