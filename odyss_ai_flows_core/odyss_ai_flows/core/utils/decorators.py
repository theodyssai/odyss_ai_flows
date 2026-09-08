# Copyright 2026 ODYSS.AI AG
# SPDX-License-Identifier: Apache-2.0
#
# See the NOTICE file for attribution information.
#
# Author:
# Aleksander Bydłowski
# abydlowski@theodyss.ai
# ai@bydlow.ski
from typing import Callable, TypeVar, ParamSpec, cast, Awaitable
from pathlib import Path


def model(cls):
    cls._is_top_model = True
    return cls


P = ParamSpec("P")
T = TypeVar("T")


def node(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:

    # Attach custom metadata directly to the original function
    setattr(func, "is_node", True)
    setattr(func, "__flow_node_path__", Path(
        func.__code__.co_filename).resolve())

    # Keep the precise callable type for Pyright/MyPy
    return cast(Callable[P, Awaitable[T]], func)
