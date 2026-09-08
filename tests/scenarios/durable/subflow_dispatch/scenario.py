from __future__ import annotations

from odyss_ai_flows_durable import PARALLEL_ORCHESTRATOR, SEQUENCE_ORCHESTRATOR, DurableFlowStep

from tests.scenarios.durable._shared.client import assert_host_available, run_orchestration
from tests.scenarios.durable._shared.flows import flow_path

_FANOUT = flow_path("fanout_router")
_FORM = flow_path("form_router")
_COLLIDE = flow_path("collide_router")


async def _router(orchestrator: str, flow: str, inputs: dict) -> dict:
    status = await run_orchestration(orchestrator, {
        "steps": [DurableFlowStep(flow_name=flow, name="router", inputs=inputs).to_dict()],
        "base_inputs": {},
    })
    assert status["runtimeStatus"] == "Completed", status.get("output")
    return status["output"]["flow_results"]["router"]


async def run_scenario() -> None:
    await assert_host_available()

    # A flat `subflows` list dispatches under the reserved "__default__" group key, and the
    # shape is identical whether the producing step ran via the sequence or parallel path.
    for orchestrator in (SEQUENCE_ORCHESTRATOR, PARALLEL_ORCHESTRATOR):
        router = await _router(orchestrator, _FANOUT, {"items": ["a", "b", "c"]})
        assert router["router"]["data"] == {"count": 3}, router["router"]
        sub = router["subflow_results"]["__default__"]
        assert sub["item_0"] == {"echo": "a"}, sub
        assert sub["item_1"] == {"echo": "b"}, sub
        assert sub["item_2"] == {"echo": "c"}, sub

    # A flat list == one explicit "__default__" group (sugar, not a separate code path).
    flat = (await _router(PARALLEL_ORCHESTRATOR, _FORM, {"form": "flat"}))["subflow_results"]
    group = (await _router(PARALLEL_ORCHESTRATOR, _FORM, {"form": "group"}))["subflow_results"]
    assert flat == {"__default__": {"item_0": {"echo": "a"}, "item_1": {"echo": "b"}}}, flat
    assert flat == group, (flat, group)

    # Same flow_name with no name -> collide (second overwrites); distinct names -> kept apart.
    unnamed = (await _router(PARALLEL_ORCHESTRATOR, _COLLIDE, {"named": False}))["subflow_results"]["batch"]
    assert len(unnamed) == 1, unnamed
    assert next(iter(unnamed.values())) == {"echo": "b"}, unnamed
    named = (await _router(PARALLEL_ORCHESTRATOR, _COLLIDE, {"named": True}))["subflow_results"]["batch"]
    assert set(named.keys()) == {"a_step", "b_step"}, named
    assert named["a_step"] == {"echo": "a"} and named["b_step"] == {"echo": "b"}, named
