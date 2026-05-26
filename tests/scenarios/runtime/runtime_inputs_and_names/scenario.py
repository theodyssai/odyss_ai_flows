from __future__ import annotations

import asyncio

from pathlib import Path

from odyss_ai_flows.core.runtime.runner import (
    run_flow,
)

from odyss_ai_flows.core.runtime.run_context import (
    current_top_run_name,
    current_top_run_id,
)

from odyss_ai_flows.core.config.utils import (
    SensitiveValue,
)

from tests.tests_runtime.assertions import (
    assert_flow_success,
)

from odyss_ai_flows.core.utils.logger import (
    logger,
)


async def run_single_flow(
    value: str,
    secret: str,
    run_name: str,
):

    result = await run_flow(

        flow=Path(
            "area/flow"
        ),

        inputs={

            "value": value,
            "secret": secret,
        },

        run_name=run_name,
    )

    assert_flow_success(result)

    return {

        "outputs": result.outputs,

        "top_run_name":
            current_top_run_name(),

        "top_run_id":
            current_top_run_id(),
    }


async def run_scenario():

    # =============================================
    # Concurrent top-level flows
    # =============================================
    
    
    from odyss_ai_flows.core.config.global_config import (
    get_raw_global_config,
    )

    logger.info(
        "RAW GLOBAL CONFIG = %r",
        get_raw_global_config(),
    )
    
    
    from odyss_ai_flows.core.config.api import cget

    logger.info(
        "GLOBAL sensitive_keys = %r",
        await cget(
            "inputs.sensitive_keys",
            default=[],
        ),
    )

    result_a, result_b = await asyncio.gather(

        run_single_flow(
            value="top_a",
            secret="secret_a",
            run_name="RUN_A",
        ),

        run_single_flow(
            value="top_b",
            secret="secret_b",
            run_name="RUN_B",
        ),
    )

    # =============================================
    # Isolation
    # =============================================

    assert (
        result_a["outputs"]["root_reader"]["value"]
        == "top_a"
    )

    assert (
        result_b["outputs"]["root_reader"]["value"]
        == "top_b"
    )

    # =============================================
    # Sensitive inputs
    # =============================================

    secret_a = (
        result_a["outputs"]["root_reader"]["secret"]
    )

    secret_b = (
        result_b["outputs"]["root_reader"]["secret"]
    )
    
    logger.info(
        "secret_a type=%s repr=%r value=%s",
        type(secret_a),
        secret_a,
        secret_a,
    )

    assert isinstance(
        secret_a,
        SensitiveValue,
    )

    assert isinstance(
        secret_b,
        SensitiveValue,
    )

    assert secret_a.unwrap() == "secret_a"
    assert secret_b.unwrap() == "secret_b"

    # =============================================
    # Default handling
    # =============================================

    defaults = (
        result_a["outputs"]["root_reader"]["defaults"]
    )

    assert defaults == {

        "single": 123,

        "tuple": [
            "top_a",
            999,
        ],
    }

    # =============================================
    # Nested lineage
    # =============================================

    nested_a = (
        result_a["outputs"]["nested_launcher_a"]
    )

    nested_b = (
        result_a["outputs"]["nested_launcher_b"]
    )

    concurrent_nested = (
        result_a["outputs"]["concurrent_launcher"]
    )

    # ---------------------------------------------
    # Top lineage preserved
    # ---------------------------------------------

    assert (
        nested_a["top_run_name"]
        == "RUN_A"
    )

    assert (
        nested_b["top_run_name"]
        == "RUN_A"
    )

    assert (
        concurrent_nested[0]["top_run_name"]
        == "RUN_A"
    )

    # ---------------------------------------------
    # Nested inputs isolated
    # ---------------------------------------------

    assert (
        nested_a["value"]
        == "nested_a"
    )

    assert (
        nested_b["value"]
        == "nested_b"
    )

    assert (
        concurrent_nested[0]["value"]
        == "concurrent_1"
    )

    assert (
        concurrent_nested[1]["value"]
        == "concurrent_2"
    )

    # ---------------------------------------------
    # Nested run names unique
    # ---------------------------------------------

    names = {

        nested_a["run_name"],
        nested_b["run_name"],
        concurrent_nested[0]["run_name"],
        concurrent_nested[1]["run_name"],
    }

    assert len(names) == 4

    # ---------------------------------------------
    # Deep nesting
    # ---------------------------------------------

    deep = nested_a["deep"]

    assert (
        deep["value"]
        == "deep_nested"
    )

    assert (
        deep["top_run_name"]
        == "RUN_A"
    )

    # =============================================
    # Context isolation between top runs
    # =============================================

    assert (
        result_a["top_run_name"]
        == "RUN_A"
    )

    assert (
        result_b["top_run_name"]
        == "RUN_B"
    )

    assert (
        result_a["top_run_id"]
        != result_b["top_run_id"]
    )