from tests.tests_runtime.requirements import requires

# Infra-free contract test: no host, but it imports the durable plugin, so gate on the
# plugin being installed (hard) — runs whenever present, skips cleanly when absent.
REQUIREMENTS = requires().plugin("odyss_ai_flows_durable")
