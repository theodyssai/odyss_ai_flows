from tests.tests_runtime.requirements import requires
from tests.scenarios.durable._shared.host_probe import durable_host_up

# durable plugin (hard prerequisite) + a probe of the Functions host (soft config gate).
REQUIREMENTS = (
    requires()
    .plugin("odyss_ai_flows_durable")
    .check("Durable test host ready on :7071", durable_host_up)
)
