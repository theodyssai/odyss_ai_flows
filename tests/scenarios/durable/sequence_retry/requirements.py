from tests.scenarios.durable._shared.host_probe import durable_host_up
from tests.tests_runtime.requirements import requires

REQUIREMENTS = (
    requires()
    .plugin("odyss_ai_flows_durable")
    .check("Durable test host ready on :7071", durable_host_up)
)
