from __future__ import annotations

from odyss_ai_flows_durable import PARALLEL_ORCHESTRATOR, DispatchMode, DurableFlowStep

from tests.scenarios.durable._shared.client import assert_host_available, run_orchestration
from tests.scenarios.durable._shared.flows import flow_path

_ECHO = flow_path("echo")
_PROBE = flow_path("probe")


async def run_scenario() -> None:
    await assert_host_available()

    # --- input isolation + result shape ---------------------------------------
    status = await run_orchestration(PARALLEL_ORCHESTRATOR, {
        "steps": [
            DurableFlowStep(flow_name=_ECHO, name="a", inputs={"message": "a"}).to_dict(),
            DurableFlowStep(flow_name=_ECHO, name="b", inputs={"message": "b"}).to_dict(),
            DurableFlowStep(flow_name=_PROBE, name="p", inputs={"message": "p"}).to_dict(),
        ],
        "base_inputs": {"shared": "S"},
    })
    assert status["runtimeStatus"] == "Completed", status.get("output")
    flow_results = status["output"]["flow_results"]

    assert flow_results["a"] == {"echo": "a"}, flow_results["a"]
    assert flow_results["b"] == {"echo": "b"}, flow_results["b"]
    # The probe saw the shared base input and its own input, but NOT any sibling's output
    # (echo_in ABSENT — no parallel step sees another's result).
    probe = flow_results["p"]["probe"]
    assert probe["message_in"] == "p" and probe["shared_in"] == "S", probe
    assert probe["echo_in"] == "ABSENT", probe

    # --- mixed DIRECT / DURABLE dispatch in one plan produces the same shape ----
    status2 = await run_orchestration(PARALLEL_ORCHESTRATOR, {
        "steps": [
            DurableFlowStep(flow_name=_ECHO, name="d", mode=DispatchMode.DIRECT,
                            inputs={"message": "d"}).to_dict(),
            DurableFlowStep(flow_name=_ECHO, name="u", mode=DispatchMode.DURABLE,
                            inputs={"message": "u"}).to_dict(),
        ],
        "base_inputs": {},
    })
    assert status2["runtimeStatus"] == "Completed", status2.get("output")
    mixed = status2["output"]["flow_results"]
    assert mixed["d"] == {"echo": "d"}, mixed["d"]
    assert mixed["u"] == {"echo": "u"}, mixed["u"]
