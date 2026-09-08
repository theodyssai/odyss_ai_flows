from odyss_ai_flows import iget, node
from odyss_ai_flows_durable import (
    DurableFlowStep,
    DurableSubflowGroup,
    DurableSubflowGroupConfig,
    DurableSubflowOutput,
)

_ECHO = "_flows/echo"
_PROBE = "_flows/probe"


@node
async def router():
    # Two staged groups: "produce" runs echo and forwards its output (needs output_keys —
    # the default [] would forward nothing); "consume" runs probe to report whether that
    # output reached it. skip_group_output on produce (set directly, or left unset to
    # inherit from default_group_config) decides whether produce's output propagates.
    skip = iget("skip", None)
    default_skip = iget("default_skip", None)

    default_config = (
        DurableSubflowGroupConfig(skip_group_output=default_skip)
        if default_skip is not None
        else None
    )

    return DurableSubflowOutput(
        data={"stage": "router"},
        default_group_config=default_config,
        groups=[
            DurableSubflowGroup(
                key="produce",
                steps=[
                    DurableFlowStep(flow_name=_ECHO, name="secret",
                                    inputs={"message": "secret"}, output_keys=["echo"])
                ],
                config=DurableSubflowGroupConfig(skip_group_output=skip),
            ),
            DurableSubflowGroup(
                key="consume",
                steps=[DurableFlowStep(flow_name=_PROBE, name="check")],
            ),
        ],
    )
