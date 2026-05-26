from odyss_ai_flows import *

import asyncio

from tests.scenarios.concurrency_and_leasing.dependency_lease_release.shared import (
    record,
)


@node
async def producer():

    await record(
        "producer:start"
    )

    await asyncio.sleep(
        0.05
    )

    await record(
        "producer:end"
    )

    return "producer_done"