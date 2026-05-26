# Copyright 2026 ODYSS.AI AG
# SPDX-License-Identifier: Apache-2.0
#
# See the NOTICE file for attribution information.
#
# Author:
# Aleksander Bydłowski
# abydlowski@theodyss.ai
# aleksander.bydlowski@gmail.com
import asyncio
from abc import ABC, abstractmethod
from typing import Any, Awaitable, Callable


class WorkStrategy(ABC):
    @abstractmethod
    async def run_node(
        self,
        name: str,
        coro_fn: Callable[[], Awaitable[Any]],
    ) -> Any:
        """
        Execute one node according to this strategy.
        """
        ...

    async def await_with_policy(self, awaitable: Awaitable[Any]) -> Any:
        """
        Await something from inside a running node.

        Default strategy has no special suspension policy.
        More advanced strategies may temporarily release execution resources
        while the current node is blocked.
        """
        return await awaitable


class DefaultWorkStrategy(WorkStrategy):
    async def run_node(
        self,
        name: str,
        coro_fn: Callable[[], Awaitable[Any]],
    ) -> Any:
        return await coro_fn()


class LeasePool:
    def __init__(self, max_concurrent: int):
        if max_concurrent <= 0:
            raise ValueError("max_concurrent must be greater than 0")

        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._task_leases: dict[asyncio.Task[Any], bool] = {}

    async def acquire(self) -> None:
        task = asyncio.current_task()
        if task is None:
            raise RuntimeError(
                "Lease acquisition requires an active asyncio task")

        await self._semaphore.acquire()
        self._task_leases[task] = True

    def release(self) -> None:
        task = asyncio.current_task()
        if task is None:
            raise RuntimeError("Lease release requires an active asyncio task")

        if self._task_leases.get(task):
            self._task_leases[task] = False
            self._semaphore.release()

    async def ensure_acquired(self) -> None:
        task = asyncio.current_task()
        if task is None:
            raise RuntimeError(
                "Lease reacquisition requires an active asyncio task")

        if not self._task_leases.get(task):
            await self.acquire()

    def has_lease(self) -> bool:
        task = asyncio.current_task()
        if task is None:
            return False

        return self._task_leases.get(task, False)


class LeasedConcurrencyStrategy(WorkStrategy):
    def __init__(self, max_concurrent: int):
        self._lease_pool = LeasePool(max_concurrent)

    async def run_node(
        self,
        name: str,
        coro_fn: Callable[[], Awaitable[Any]],
    ) -> Any:
        await self._lease_pool.acquire()
        try:
            return await coro_fn()
        finally:
            self._lease_pool.release()

    async def await_with_policy(self, awaitable: Awaitable[Any]) -> Any:
        if not self._lease_pool.has_lease():
            return await awaitable

        self._lease_pool.release()
        try:
            return await awaitable
        finally:
            await self._lease_pool.ensure_acquired()
