from __future__ import annotations

import os

from pathlib import Path

from odyss_ai_flows.core.runtime.runner import (
    run_flow,
)

from odyss_ai_flows.core.config.providers import (
    clear_providers,
    register_provider,
)

from odyss_ai_flows.core.config.utils import (
    SensitiveValue,
)

from tests.tests_runtime.assertions import (
    assert_flow_success,
)


# -------------------------------------------------
# Mock providers
# -------------------------------------------------

async def MOCK_SECRET(key: str):

    return f"secret::{key}"


async def run_scenario():

    # =============================================
    # Providers
    # =============================================

    clear_providers()

    from odyss_ai_flows.core.config.providers import (
        ENV,
        LITERAL_SECRET,
    )

    register_provider(
        "ENV",
        ENV,
    )

    register_provider(
        "LITERAL_SECRET",
        LITERAL_SECRET,
        sensitive=True,
    )

    register_provider(
        "SECRET",
        MOCK_SECRET,
        sensitive=True,
    )

    # =============================================
    # Lazy runtime
    # =============================================

    result = await run_flow(

        flow=Path(
            "area/flow"
        ),
    )

    assert_flow_success(result)

    runtime = result[
        "runtime_node"
    ]

    # =============================================
    # Direct secret
    # =============================================

    direct = runtime[
        "direct"
    ]

    assert isinstance(
        direct,
        SensitiveValue,
    )

    assert direct.unwrap() == (
        "secret::token"
    )

    # =============================================
    # REF -> secret
    # =============================================

    refed = runtime[
        "refed"
    ]

    assert isinstance(
        refed,
        SensitiveValue,
    )

    assert refed.unwrap() == (
        "secret::token"
    )