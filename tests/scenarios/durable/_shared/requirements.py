from __future__ import annotations

from tests.scenarios.durable._shared.host_probe import durable_host_up
from tests.tests_runtime.requirements import (
    CustomRequirement,
    custom,
)


def durable_host_requirement() -> CustomRequirement:
    """The suite-wide Durable Functions host readiness gate."""

    return custom(
        durable_host_up,
        "Durable test host ready on :7071",
        cache_key="durable-test-host-readiness",
    )
