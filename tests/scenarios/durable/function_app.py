from __future__ import annotations

import json

import azure.durable_functions as df
import azure.functions as func

from odyss_ai_flows_durable import (
    FLOW_ORCHESTRATOR,
    DurableHttpEventClient,
    register_durable_support,
)

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

bp = df.Blueprint()


@app.route(route="durable-test-health", methods=["GET"])
def durable_test_health(req: func.HttpRequest) -> func.HttpResponse:
    """Identify this exact test host without starting an orchestration."""
    del req
    return func.HttpResponse(
        json.dumps({
            "service": "odyss-ai-flows-durable-test-host",
            "orchestrators": [FLOW_ORCHESTRATOR],
        }),
        status_code=200,
        mimetype="application/json",
    )


# The node-signalling event client is configured explicitly rather than via global_config.json
# so the suite needs no config file in the host cwd. The URL is the bare host (no /api) — the
# client appends the /runtime/webhooks/durabletask/... path itself.
event_client = DurableHttpEventClient(management_url="http://localhost:7071")

# Native node-activity retry (RetryOptions(5_000, 3)) is disabled so that an explicit
# DurableRetryPolicy is the sole, deterministic retry layer the durable tests exercise
# (otherwise the native 5s x 3 layer recovers failures before a policy is ever engaged).
register_durable_support(bp, event_client=event_client, retry_options=df.RetryOptions(10, 1))

app.register_blueprint(bp)
