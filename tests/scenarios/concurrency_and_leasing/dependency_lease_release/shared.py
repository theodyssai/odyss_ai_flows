import asyncio


LOCK = asyncio.Lock()

EVENTS = []


async def record(event: str):

    async with LOCK:

        EVENTS.append(event)


async def reset():

    async with LOCK:

        EVENTS.clear()