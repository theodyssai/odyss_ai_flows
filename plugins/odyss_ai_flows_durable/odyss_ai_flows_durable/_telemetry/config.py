from __future__ import annotations

from odyss_ai_flows.core.config.global_config import get_global_setting

_KEY = "durable.telemetry.enabled"


async def is_telemetry_enabled() -> bool:
    value = await get_global_setting(_KEY, default=False)
    return bool(value)
