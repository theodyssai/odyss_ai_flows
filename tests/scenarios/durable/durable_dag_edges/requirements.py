from tests.scenarios.durable._shared.requirements import durable_host_requirement
from tests.tests_runtime.requirements import requires

REQUIREMENTS = (
    requires()
    .plugin("odyss_ai_flows_durable")
    .add(durable_host_requirement())
)
