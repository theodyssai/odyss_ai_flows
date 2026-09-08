from __future__ import annotations

from pathlib import Path

from odyss_ai_flows_durable import SEQUENCE_ORCHESTRATOR, DispatchMode, DurableFlowStep

from tests.scenarios.durable._shared.client import assert_host_available, run_orchestration
from tests.scenarios.durable._shared.flows import host_relative

_SCENARIO_DIR = Path(__file__).parent

_CHAIN_STEP = host_relative(_SCENARIO_DIR / "chain_step")

_DEPTH = 4


async def run_scenario() -> None:
    await assert_host_available()

    steps = [
        DurableFlowStep(
            flow_name=_CHAIN_STEP,
            mode=DispatchMode.DIRECT,
            name=f"s{i}",
            inputs={"suffix": f"_{i}"},
            output_keys=["current"],
        ).to_dict()
        for i in range(1, _DEPTH + 1)
    ]

    payload = {
        "steps": steps,
        "base_inputs": {"current": "start"},
    }

    status = await run_orchestration(SEQUENCE_ORCHESTRATOR, payload)

    assert status["runtimeStatus"] == "Completed", status.get("output")

    flow_results = status["output"]["flow_results"]

    expected = "start" + "".join(f"_{i}" for i in range(1, _DEPTH + 1))

    assert flow_results[f"s{_DEPTH}"]["current"] == expected, (
        f"Expected '{expected}', got '{flow_results[f's{_DEPTH}']['current']}'"
    )
