import asyncio


LOCK = asyncio.Lock()

CURRENT_ACTIVE = 0
MAX_ACTIVE = 0
COMPLETED = 0


async def enter():

    global CURRENT_ACTIVE
    global MAX_ACTIVE

    async with LOCK:

        CURRENT_ACTIVE += 1

        if CURRENT_ACTIVE > MAX_ACTIVE:

            MAX_ACTIVE = CURRENT_ACTIVE


async def leave():

    global CURRENT_ACTIVE
    global COMPLETED

    async with LOCK:

        CURRENT_ACTIVE -= 1
        COMPLETED += 1


async def reset():

    global CURRENT_ACTIVE
    global MAX_ACTIVE
    global COMPLETED

    async with LOCK:

        CURRENT_ACTIVE = 0
        MAX_ACTIVE = 0
        COMPLETED = 0