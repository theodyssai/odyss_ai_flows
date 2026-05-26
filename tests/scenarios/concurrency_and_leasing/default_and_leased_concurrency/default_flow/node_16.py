from odyss_ai_flows import *

import asyncio

from tests.scenarios.concurrency_and_leasing.default_and_leased_concurrency.shared import (
    enter,
    leave,
)


@node
async def node_16():

    await enter()

    try:

        await asyncio.sleep(
            0.05
        )

        return 16

    finally:

        await leave()