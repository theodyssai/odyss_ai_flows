from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

from odyss_ai_flows.core.config.global_config import get_global_setting

_DEFAULT_TIMEOUT = 30.0


class DurableHttpEventClient:
    def __init__(
        self,
        management_url: str | None = None,
        system_key: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self._management_url = management_url
        self._system_key = system_key
        self._timeout_seconds = timeout_seconds

    async def raise_event(
        self,
        instance_id: str,
        event_name: str,
        data: Any,
    ) -> None:
        management_url = (
            self._management_url
            or await get_global_setting("durable.management_url")
            or ""
        ).rstrip("/")

        system_key = (
            self._system_key
            or await get_global_setting("durable.system_key")
            or ""
        )

        timeout = (
            self._timeout_seconds
            or await get_global_setting("durable.timeout_seconds")
            or _DEFAULT_TIMEOUT
        )

        if not management_url:
            raise RuntimeError(
                "Durable management URL is missing. "
                "Set 'durable.management_url' in global_config.json "
                "or pass management_url explicitly."
            )

        is_local = (
            management_url.startswith("http://localhost")
            or management_url.startswith("http://127.0.0.1")
        )

        if not system_key and not is_local:
            raise RuntimeError(
                "Durable system key is missing. "
                "Set 'durable.system_key' in global_config.json "
                "or pass system_key explicitly."
            )

        encoded_instance_id = quote(instance_id, safe="")
        encoded_event_name = quote(event_name, safe="")

        base_url = (
            f"{management_url}"
            f"/runtime/webhooks/durabletask/instances/{encoded_instance_id}"
            f"/raiseEvent/{encoded_event_name}"
        )
        url = f"{base_url}?code={system_key}" if system_key else base_url

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=data)
            response.raise_for_status()
