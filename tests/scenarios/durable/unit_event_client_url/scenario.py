from __future__ import annotations

from unittest.mock import patch

import odyss_ai_flows_durable._runtime._single.http_event_client as hec
from odyss_ai_flows_durable import DurableHttpEventClient


class _FakeResponse:
    def raise_for_status(self) -> None:
        return None


class _FakeAsyncClient:
    """Captures the URL that raise_event posts to, without any real HTTP."""

    last_url: str | None = None

    def __init__(self, *args, **kwargs) -> None:
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, url, json=None):
        _FakeAsyncClient.last_url = url
        return _FakeResponse()


async def _no_config(key, default=None):
    return None


async def run_scenario() -> None:
    with patch.object(hec.httpx, "AsyncClient", _FakeAsyncClient), \
         patch.object(hec, "get_global_setting", _no_config):

        # Bare localhost host, no key: path appended, instance/event percent-encoded, no ?code.
        _FakeAsyncClient.last_url = None
        await DurableHttpEventClient(management_url="http://localhost:7071").raise_event(
            "inst-1", "dep:consumer", {"r": 1}
        )
        assert _FakeAsyncClient.last_url == (
            "http://localhost:7071/runtime/webhooks/durabletask/instances/inst-1"
            "/raiseEvent/dep%3Aconsumer"
        ), _FakeAsyncClient.last_url

        # A trailing slash on management_url is stripped (no doubled slash).
        _FakeAsyncClient.last_url = None
        await DurableHttpEventClient(management_url="http://localhost:7071/").raise_event(
            "inst-1", "evt", {}
        )
        assert _FakeAsyncClient.last_url == (
            "http://localhost:7071/runtime/webhooks/durabletask/instances/inst-1/raiseEvent/evt"
        ), _FakeAsyncClient.last_url

        # Non-localhost with a system key: ?code=<key> appended.
        _FakeAsyncClient.last_url = None
        await DurableHttpEventClient(
            management_url="https://app.azurewebsites.net", system_key="SECRET"
        ).raise_event("inst-1", "evt", {})
        assert _FakeAsyncClient.last_url.endswith(
            "/runtime/webhooks/durabletask/instances/inst-1/raiseEvent/evt?code=SECRET"
        ), _FakeAsyncClient.last_url

        # Non-localhost WITHOUT a key: raises before any HTTP.
        raised_key = False
        try:
            await DurableHttpEventClient(
                management_url="https://app.azurewebsites.net"
            ).raise_event("inst-1", "evt", {})
        except RuntimeError as exc:
            raised_key = "system key is missing" in str(exc)
        assert raised_key, "expected a missing-system-key RuntimeError"

        # No management_url anywhere: raises the missing-URL error.
        raised_url = False
        try:
            await DurableHttpEventClient().raise_event("inst-1", "evt", {})
        except RuntimeError as exc:
            raised_url = "management URL is missing" in str(exc)
        assert raised_url, "expected a missing-management-URL RuntimeError"
