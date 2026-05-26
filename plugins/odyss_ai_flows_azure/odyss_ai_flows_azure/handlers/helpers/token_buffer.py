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
import contextvars
from typing import Dict, Optional


class AsyncBuffer:
    def __init__(self):
        self._queue = asyncio.Queue()
        self._closed = asyncio.Event()

    async def write(self, token: str):
        await self._queue.put(token)

    async def read(self) -> str:
        return await self._queue.get()

    def close(self):
        self._closed.set()

    async def wait_closed(self):
        await self._closed.wait()

    def is_closed(self) -> bool:
        return self._closed.is_set()


_CURRENT_STREAM_BUFFER = contextvars.ContextVar(
    "CURRENT_STREAM_BUFFER", default=None)


def set_current_stream_buffer(buffers: Dict[str, AsyncBuffer]):
    _CURRENT_STREAM_BUFFER.set(buffers)


def get_current_stream_buffer() -> Optional[Dict[str, AsyncBuffer]]:
    return _CURRENT_STREAM_BUFFER.get()


def get_node_stream_buffer(node_name: str) -> Optional[AsyncBuffer]:
    buffers = get_current_stream_buffer()
    return buffers.get(node_name) if buffers else None


def list_active_stream_nodes() -> list[str]:
    buffers = get_current_stream_buffer()
    return list(buffers.keys()) if buffers else []
