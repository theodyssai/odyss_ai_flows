from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

HOST_URL = "http://localhost:7071"
HEALTH_URL = f"{HOST_URL}/api/durable-test-health"
_EXPECTED_SERVICE = "odyss-ai-flows-durable-test-host"
_EXPECTED_ORCHESTRATOR = "flow_orchestrator"
FUNCTION_REGISTRATION_URL = (
    f"{HOST_URL}/admin/functions/{_EXPECTED_ORCHESTRATOR}"
)


def is_expected_host_health(status_code: int, payload: object) -> bool:
    if status_code != 200 or not isinstance(payload, dict):
        return False

    orchestrators = payload.get("orchestrators")
    return (
        payload.get("service") == _EXPECTED_SERVICE
        and isinstance(orchestrators, list)
        and _EXPECTED_ORCHESTRATOR in orchestrators
    )


def is_expected_function_registration(status_code: int, payload: object) -> bool:
    if status_code != 200 or not isinstance(payload, dict):
        return False

    config = payload.get("config")
    if not isinstance(config, dict):
        return False

    bindings = config.get("bindings")
    if not isinstance(bindings, list):
        return False

    return (
        payload.get("name") == _EXPECTED_ORCHESTRATOR
        and any(
            isinstance(binding, dict)
            and binding.get("type") == "orchestrationTrigger"
            and binding.get("orchestration") == _EXPECTED_ORCHESTRATOR
            for binding in bindings
        )
    )


def _read_json(url: str) -> tuple[int, object]:
    with urlopen(url, timeout=3) as response:
        return response.status, json.load(response)


def durable_host_up(scenario_dir=None) -> tuple[bool, str]:
    """Verify that port 7071 belongs to this suite's fully registered test host."""
    del scenario_dir

    try:
        health_status, health_payload = _read_json(HEALTH_URL)
        registration_status, registration_payload = _read_json(
            FUNCTION_REGISTRATION_URL
        )
    except HTTPError as exc:
        return False, (
            "Durable test host endpoint is unavailable on :7071 "
            f"(HTTP {exc.code}; run azurite + func start from tests/scenarios/durable/)"
        )
    except (URLError, OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        return False, (
            "Durable test host is unavailable on :7071 "
            f"({type(exc).__name__}: {exc}; run azurite + func start)"
        )

    if not is_expected_host_health(health_status, health_payload):
        return False, (
            "Port 7071 is not the odyss durable test host "
            "(health identity mismatch)"
        )

    if not is_expected_function_registration(
        registration_status,
        registration_payload,
    ):
        return False, (
            "The odyss durable test host does not expose the expected "
            "flow_orchestrator binding"
        )

    return True, "Durable test host ready on :7071 (flow_orchestrator registered)"
