from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

from odyss_ai_flows.core.runtime.runner import (
    run_flow,
)

from tests.tests_runtime.assertions import (
    assert_flow_success,
)


async def run_scenario():

    # =============================================
    # Explicit dotenv bootstrap
    # =============================================

    env_path = (
        Path(__file__)
        .parent
        / ".env.local"
    )

    load_dotenv(
        env_path,
        override=True,
    )

    # =============================================
    # Execute flow
    # =============================================

    result = await run_flow(
        "hello_flow"
    )

    # =============================================
    # Assertions
    # =============================================

    assert_flow_success(
        result
    )

    text = result[
        "hello"
    ]

    assert (
        "HELLO_WORLD_OK"
        in text
    )