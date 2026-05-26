# Copyright 2026 ODYSS.AI AG
# SPDX-License-Identifier: Apache-2.0
#
# See the NOTICE file for attribution information.
#
# Author:
# Aleksander Bydłowski
# abydlowski@theodyss.ai
# aleksander.bydlowski@gmail.com
from functools import wraps
from time import perf_counter
from typing import Any, Awaitable, Callable

RunFn = Callable[..., Awaitable[Any]]


def logging_middleware(next_call: RunFn, handler) -> RunFn:
    @wraps(next_call)
    async def wrapper(**kwargs: Any) -> Any:
        node = getattr(handler, "node", None)
        name = getattr(node, "name", getattr(
            handler, "__class__", type(handler)).__name__)
        scope = getattr(node, "scope", "?")
        logger = getattr(handler, "logger", None)

        msg_start = f"[LOGGING] {name} start (scope={scope})"
        msg_done = f"[LOGGING] {name} done"
        if logger:
            logger.info(msg_start)
        else:
            print(msg_start)

        try:
            return await next_call(**kwargs)
        finally:
            if logger:
                logger.info(msg_done)
            else:
                print(msg_done)
    return wrapper


def timing_middleware(next_call: RunFn, handler) -> RunFn:
    @wraps(next_call)
    async def wrapper(**kwargs: Any) -> Any:
        t0 = perf_counter()
        result = await next_call(**kwargs)
        dt = perf_counter() - t0
        node = getattr(handler, "node", None)
        name = getattr(node, "name", type(handler).__name__)
        logger = getattr(handler, "logger", None)
        msg = f"[TIMING] {name} took {dt:.2f}s"
        if logger:
            logger.info(msg)
        else:
            print(msg)
        return result
    return wrapper


def register_all(register_fn):
    register_fn("logging", logging_middleware)
    register_fn("timing", timing_middleware)
