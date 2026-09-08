from __future__ import annotations

import asyncio
import time
from typing import Any
from urllib.parse import quote

import httpx

from tests.scenarios.durable._shared.host_probe import (
    FUNCTION_REGISTRATION_URL,
    HEALTH_URL,
    HOST_URL,
    is_expected_function_registration,
    is_expected_host_health,
)

_ORCHESTRATORS_BASE = f"{HOST_URL}/runtime/webhooks/durabletask/orchestrators"
_INSTANCES_BASE = f"{HOST_URL}/runtime/webhooks/durabletask/instances"
_TERMINAL = {"Completed", "Failed", "Terminated", "Canceled"}


async def is_host_available() -> bool:
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            health = await client.get(HEALTH_URL)
            registration = await client.get(FUNCTION_REGISTRATION_URL)
            return (
                is_expected_host_health(health.status_code, health.json())
                and is_expected_function_registration(
                    registration.status_code,
                    registration.json(),
                )
            )
    except Exception:
        return False


async def assert_host_available() -> None:
    if not await is_host_available():
        raise RuntimeError(
            "Azure Functions host is not reachable at http://localhost:7071. "
            "Run 'func start' from tests/scenarios/durable/ before executing durable tests."
        )


async def start_orchestration(
    orchestrator_name: str,
    input_data: dict[str, Any],
    *,
    instance_id: str | None = None,
) -> dict[str, Any]:
    url = f"{_ORCHESTRATORS_BASE}/{orchestrator_name}"
    if instance_id:
        url = f"{url}/{instance_id}"

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=input_data)
        resp.raise_for_status()
        return resp.json()


async def wait_for_completion(
    status_url: str,
    *,
    timeout: float = 60.0,
    poll_interval: float = 0.5,
) -> dict[str, Any]:
    status = await wait_for_terminal(
        status_url,
        timeout=timeout,
        poll_interval=poll_interval,
    )

    if status is not None:
        return status

    raise TimeoutError(
        f"Orchestration did not reach a terminal state within {timeout}s"
    )


async def wait_for_terminal(
    status_url: str,
    *,
    timeout: float,
    poll_interval: float = 0.5,
) -> dict[str, Any] | None:
    """Return terminal status, or None when the caller's bounded wait expires."""
    deadline = time.monotonic() + timeout

    async with httpx.AsyncClient() as client:
        while time.monotonic() < deadline:
            resp = await client.get(status_url)
            resp.raise_for_status()

            status = resp.json()

            if status["runtimeStatus"] in _TERMINAL:
                return status

            await asyncio.sleep(poll_interval)

    return None


async def get_instance_status(instance_id: str) -> dict[str, Any]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(_instance_status_url(instance_id))
        resp.raise_for_status()
        return resp.json()


async def wait_for_instance_completion(
    instance_id: str,
    *,
    timeout: float = 60.0,
) -> dict[str, Any]:
    return await wait_for_completion(
        _instance_status_url(instance_id),
        timeout=timeout,
    )


async def terminate_instance(
    instance_id: str,
    *,
    reason: str,
) -> None:
    url = (
        f"{_instance_status_url(instance_id)}/terminate"
        f"?reason={quote(reason, safe='')}"
    )
    async with httpx.AsyncClient() as client:
        resp = await client.post(url)
        resp.raise_for_status()


async def terminate_orchestration(
    terminate_url: str,
    *,
    reason: str,
) -> None:
    url = terminate_url.replace("{text}", quote(reason, safe=""))
    async with httpx.AsyncClient() as client:
        resp = await client.post(url)
        resp.raise_for_status()


def _instance_status_url(instance_id: str) -> str:
    encoded_instance_id = quote(instance_id, safe="")
    return f"{_INSTANCES_BASE}/{encoded_instance_id}"


async def run_orchestration(
    orchestrator_name: str,
    input_data: dict[str, Any],
    *,
    timeout: float = 60.0,
) -> dict[str, Any]:
    start_resp = await start_orchestration(orchestrator_name, input_data)
    status_url = start_resp["statusQueryGetUri"]
    return await wait_for_completion(status_url, timeout=timeout)
