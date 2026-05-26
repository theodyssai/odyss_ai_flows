from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

from odyss_ai_flows.core.runtime.runner import (
    run_flow,
)

from odyss_ai_flows.core.utils.logger import (
    logger,
)

from tests.tests_runtime.assertions import (
    assert_flow_success,
)


async def run_scenario():

    # =====================================================
    # Explicit dotenv bootstrap
    # =====================================================

    env_path = (
        Path(__file__)
        .parent
        / ".env.local"
    )

    load_dotenv(
        env_path,
        override=True,
    )

    logger.info(
        "[scenario] dotenv loaded from: %s",
        env_path,
    )

    # =====================================================
    # Execute flow
    # =====================================================

    logger.info(
        "[scenario] starting composed_jinja_flow"
    )

    result = await run_flow(
        "main_flow",
        inputs={
            "name": "Alek"
        },
    )

    logger.info(
        "[scenario] flow completed"
    )

    # =====================================================
    # Assertions
    # =====================================================

    assert_flow_success(
        result
    )

    logger.info(
        "[scenario] flow success confirmed"
    )

    # =====================================================
    # Debug outputs
    # =====================================================

    intro = result["intro"]
    processor = result["processor"]
    final = result["final"]

    logger.info(
        "[scenario] intro result:\n%s",
        intro,
    )

    logger.info(
        "[scenario] processor result:\n%s",
        processor,
    )

    logger.info(
        "[scenario] final result:\n%s",
        final,
    )

    # =====================================================
    # Validation
    # =====================================================

    assert (
        "INPUT=ALEK"
        in final
    )

    assert (
        "CONFIG=CONFIG_OK"
        in final
    )

    assert (
        "NESTED_OK"
        in final
    )

    assert (
        "FINAL_OK"
        in final
    )

    logger.info(
        "[scenario] all assertions passed"
    )