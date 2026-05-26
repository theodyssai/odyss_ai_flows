# tests/scenarios/hello_world_basic/scenario.py

from __future__ import annotations

from pathlib import Path

from tests.tests_runtime.assertions import (
    assert_flow_success,
    assert_output_equals,
)

from tests.tests_runtime.scenario_protocol import (
    ScenarioRuntimeDefinition,
)


# ---------------------------------------------------------
# Flow location
# ---------------------------------------------------------

FLOW_DIR = (
    Path(__file__).parent
    / "flow"
)


# ---------------------------------------------------------
# Runtime definition
# ---------------------------------------------------------

runtime = ScenarioRuntimeDefinition(

    flow=FLOW_DIR,

    assertions=[

        assert_flow_success,

        lambda result: assert_output_equals(
            result,
            "hello",
            "hello world",
        ),
    ],

    metadata={
        "category": "basic",
        "description": (
            "Minimal filesystem-based "
            "hello world flow"
        ),
    },
)