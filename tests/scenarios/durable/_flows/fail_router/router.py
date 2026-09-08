from odyss_ai_flows import iget, node
from odyss_ai_flows_durable import DurableFlowStep, DurableSubflowOutput

_ECHO = "_flows/echo"
_FLAKY = "_flows/flaky"


@node
async def router():
    # Dispatches one healthy subflow and one failing one. With fail_times and a
    # DurableRetryPolicy on the request, whether "bad" recovers tells us if the executor's
    # policy reaches *subflow* steps or only top-level plan steps (§4.2).
    run_id = iget("run_id", "default")
    fail_times = int(iget("fail_times", 99))

    return DurableSubflowOutput(
        data={"dispatched": 2},
        subflows=[
            DurableFlowStep(flow_name=_ECHO, name="ok", inputs={"message": "ok"}),
            DurableFlowStep(flow_name=_FLAKY, name="bad",
                            inputs={"run_id": run_id, "fail_times": fail_times}),
        ],
    )
