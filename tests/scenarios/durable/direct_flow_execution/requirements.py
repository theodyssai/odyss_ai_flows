from tests.tests_runtime.requirements import requires

# Infra-free, but this scenario exercises the durable plugin's no-executor entry point.
REQUIREMENTS = requires().plugin("odyss_ai_flows_durable")
