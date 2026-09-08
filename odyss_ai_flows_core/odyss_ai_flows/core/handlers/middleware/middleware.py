# Copyright 2026 ODYSS.AI AG
# SPDX-License-Identifier: Apache-2.0
#
# See the NOTICE file for attribution information.
#
# Author:
# Aleksander Bydłowski
# abydlowski@theodyss.ai
# ai@bydlow.ski
from __future__ import annotations
from functools import wraps
from typing import Any, Awaitable, Callable, Dict, TYPE_CHECKING
from odyss_ai_flows.core.config.api import cget

if TYPE_CHECKING:
    from odyss_ai_flows.core.handlers.base import AbstractHandler

RunFn = Callable[..., Awaitable[Any]]
Middleware = Callable[[RunFn, "AbstractHandler"], RunFn]

REGISTERED_MIDDLEWARES: Dict[str, Middleware] = {}


def register_middleware(name: str, wrapper_fn: Middleware) -> None:
    if name in REGISTERED_MIDDLEWARES:
        raise ValueError(f"Middleware '{name}' already registered")
    REGISTERED_MIDDLEWARES[name] = wrapper_fn


async def apply_middleware(fn: RunFn, handler: "AbstractHandler") -> RunFn:

    names = await cget("middleware", [])
    call = fn
    for mw_name in reversed(names):
        mw = REGISTERED_MIDDLEWARES.get(mw_name)
        if not mw:
            raise ValueError(f"Middleware '{mw_name}' is not registered")
        call = mw(call, handler)

    @wraps(fn)
    async def wrapper(**kwargs: Any) -> Any:
        return await call(**kwargs)

    return wrapper
