# Copyright 2026 ODYSS.AI AG
# SPDX-License-Identifier: Apache-2.0
#
# See the NOTICE file for attribution information.
#
# Author:
# Aleksander Bydłowski
# abydlowski@theodyss.ai
# ai@bydlow.ski
from pathlib import Path
from typing import Any, Callable, Union, Awaitable, TypeVar, overload

from odyss_ai_flows.core.executor.execution_context import get_executor

T = TypeVar("T")


# --- overloads ---

@overload
async def nget(ref: str) -> Any: ...
@overload
async def nget(ref: Callable[..., Awaitable[T]]) -> T: ...
@overload
async def nget(ref: str, fn: Callable[..., Awaitable[T]]) -> T: ...


# --- implementation ---

async def nget(
    ref: Union[str, Callable[..., Any]],
    fn: Callable[..., Any] | None = None
) -> Any:
    executor = get_executor()
    if executor is None:
        raise RuntimeError("nget() called outside of an active execution context")

    node_states = executor.node_states

    # ---------------------------------------------------------
    # MODE 1: (name, function) → name is authoritative
    # ---------------------------------------------------------
    if isinstance(ref, str) and fn is not None:
        name = ref

        if name not in node_states:
            raise ValueError(f"nget(): node '{name}' is not a known node in this flow")

        # function is intentionally ignored (only for typing / reference)
        return await executor.await_dependency(name)

    # ---------------------------------------------------------
    # MODE 2: string → canonical
    # ---------------------------------------------------------
    if isinstance(ref, str):
        name = ref

        if name not in node_states:
            raise ValueError(f"nget(): node '{name}' is not a known node in this flow")

        return await executor.await_dependency(name)

    # ---------------------------------------------------------
    # MODE 3: function → dual resolver with ambiguity checks
    # ---------------------------------------------------------
    if callable(ref):
        fn = ref

        if not getattr(fn, "is_node", False):
            raise TypeError("nget(): function is not marked with @node")

        # --- FIRST: callable-based resolution ---
        key = id(fn)
        names = executor.callable_to_node_map.get(key)

        if names:
            if len(names) > 1:
                raise ValueError(
                    f"nget(): function '{fn.__name__}' is ambiguous "
                    f"(matches nodes: {names})"
                )
            return await executor.await_dependency(names[0])

        # --- SECOND: path-based resolution ---
        func_path = getattr(fn, "__flow_node_path__", None)
        if isinstance(func_path, Path):
            func_path = func_path.resolve()
            names = executor.path_to_node_map.get(func_path)

            if names:
                if len(names) > 1:
                    raise ValueError(
                        f"nget(): function '{fn.__name__}' is ambiguous via path "
                        f"(matches nodes: {names})"
                    )
                return await executor.await_dependency(names[0])

        # --- FAILURE ---
        raise ValueError(
            f"nget(): cannot resolve function '{fn.__name__}' to any node. "
            f"Use nget('<name>') or nget('<name>', fn)."
        )

    # ---------------------------------------------------------
    # INVALID INPUT
    # ---------------------------------------------------------
    raise TypeError(f"nget(): unsupported reference type: {type(ref)}")











