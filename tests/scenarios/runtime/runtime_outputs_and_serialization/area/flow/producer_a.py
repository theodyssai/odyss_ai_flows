from odyss_ai_flows import *

from tests.scenarios.runtime.runtime_outputs_and_serialization.helpers.objects import (
    ComplexObject,
)


@node
async def producer_a():

    return ComplexObject(
        123
    )