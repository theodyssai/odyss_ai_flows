from __future__ import annotations

from odyss_ai_flows_durable import SEQUENCE_ORCHESTRATOR, DispatchMode, DurableFlowStep

from tests.scenarios.durable._shared.client import assert_host_available, run_orchestration
from tests.scenarios.durable._shared.flows import flow_path

_ECHO = flow_path("echo")
_PROBE = flow_path("probe")


async def _echo_in_after(output_keys: list[str]) -> str:
    # step "a" (echo) emits {"echo": "secret"}; its output_keys decide what forwards to "b"
    # (probe), which reports whether "echo" arrived in its inputs.
    status = await run_orchestration(SEQUENCE_ORCHESTRATOR, {
        "steps": [
            DurableFlowStep(flow_name=_ECHO, name="a", mode=DispatchMode.DIRECT,
                            inputs={"message": "secret"}, output_keys=output_keys).to_dict(),
            DurableFlowStep(flow_name=_PROBE, name="b").to_dict(),
        ],
        "base_inputs": {},
    })
    assert status["runtimeStatus"] == "Completed", status.get("output")
    return status["output"]["flow_results"]["b"]["probe"]["echo_in"]


async def run_scenario() -> None:
    await assert_host_available()

    # input_keys is an allow-list filtering which base_inputs a step receives.
    status = await run_orchestration(SEQUENCE_ORCHESTRATOR, {
        "steps": [DurableFlowStep(flow_name=_PROBE, name="p", input_keys=["shared"]).to_dict()],
        "base_inputs": {"shared": "S", "message": "M"},
    })
    assert status["runtimeStatus"] == "Completed", status.get("output")
    probe = status["output"]["flow_results"]["p"]["probe"]
    assert probe["shared_in"] == "S", probe          # allowed through
    assert probe["message_in"] == "ABSENT", probe    # filtered out

    # output_keys forwards a step's selected node outputs to later steps; the default [] (no
    # output_keys) forwards nothing. This also crosses dispatch modes: the producer is DIRECT
    # and the downstream probe is DURABLE.
    assert await _echo_in_after(["echo"]) == "secret"
    assert await _echo_in_after([]) == "ABSENT"

    # Two same-flow steps without name= share the flow path as their result key, so the
    # second silently overwrites the first. Distinct names elsewhere in this suite prove
    # the supported way to avoid the collision.
    collision = await run_orchestration(SEQUENCE_ORCHESTRATOR, {
        "steps": [
            DurableFlowStep(
                flow_name=_ECHO,
                mode=DispatchMode.DIRECT,
                inputs={"message": "first"},
            ).to_dict(),
            DurableFlowStep(
                flow_name=_ECHO,
                mode=DispatchMode.DIRECT,
                inputs={"message": "second"},
            ).to_dict(),
        ],
        "base_inputs": {},
    })
    assert collision["runtimeStatus"] == "Completed", collision.get("output")
    collided_results = collision["output"]["flow_results"]
    assert collided_results == {_ECHO: {"echo": "second"}}, collided_results
