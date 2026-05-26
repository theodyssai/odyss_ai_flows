from odyss_ai_flows import *

import asyncio

from tests.scenarios.concurrency_and_leasing.dependency_lease_release.flow.producer import (
    producer,
)

from tests.scenarios.concurrency_and_leasing.dependency_lease_release.shared import (
    record,
)


@node
async def consumer_3():

    await record(
        "consumer_3:start"
    )

    await asyncio.sleep(
        0.02
    )

    value = await nget(
        producer
    )

    await record(
        "consumer_3:resumed"
    )

    return value