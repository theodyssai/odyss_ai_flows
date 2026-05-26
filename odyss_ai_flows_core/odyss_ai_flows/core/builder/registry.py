# Copyright 2026 ODYSS.AI AG
# SPDX-License-Identifier: Apache-2.0
#
# See the NOTICE file for attribution information.
#
# Author:
# Aleksander Bydłowski
# abydlowski@theodyss.ai
# aleksander.bydlowski@gmail.com
from typing import Type

from odyss_ai_flows.core.handlers.base import AbstractHandler


handler_registry: dict[str, Type[AbstractHandler]] = {}
node_kinds: set[str] = {"python", "jinja"}


def register_handler(name: str, constructor: Type[AbstractHandler]) -> None:
    handler_registry[name] = constructor


def register_node_kind(kind: str) -> None:
    node_kinds.add(kind)


def get_handler(name: str) -> Type[AbstractHandler]:
    if name not in handler_registry:
        raise ValueError(f"No handler registered under name '{name}'")
    return handler_registry[name]


def get_node_kinds() -> set[str]:
    return set(node_kinds)


def _register_builtin_handlers() -> None:
    from odyss_ai_flows.core.handlers.python_handler import PythonHandler
    from odyss_ai_flows.core.handlers.llm.composed_handler import ComposedHandler

    handler_registry.update({
        "python": PythonHandler,
        "jinja": ComposedHandler,
    })


_register_builtin_handlers()
