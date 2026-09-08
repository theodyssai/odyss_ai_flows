from __future__ import annotations

from functools import wraps
from typing import Any, Awaitable, Callable

from odyss_ai_flows.core.config.api import cget
from odyss_ai_flows.core.handlers.llm.connection import resolve_llm_connection
from odyss_ai_flows.core.utils.logger import logger

from odyss_ai_flows_token_limiter.redis_factory import get_redis_client
from odyss_ai_flows_token_limiter.store import (
    TokenLimitExceeded,
    raise_if_token_limit_exceeded,
    update_all_token_counters,
)

RunFn = Callable[..., Awaitable[Any]]


async def _resolve_deployment() -> str:
    connection = await resolve_llm_connection()
    return connection.get("deployment_name") or "default"


def token_limiter(next_call: RunFn, handler) -> RunFn:
    @wraps(next_call)
    async def wrapper(**kwargs: Any) -> Any:
        config = await cget("token_limiter", default={}) or {}

        if not config:
            return await next_call(**kwargs)

        redis_config = await cget("redis", default={}) or {}
        redis_client = await get_redis_client(redis_config)
        deployment_id = await _resolve_deployment()

        try:
            await raise_if_token_limit_exceeded(deployment_id, config, redis_client)
        except TokenLimitExceeded as exc:
            logger.error(f"{handler.node.name} - input token limit exceeded: {exc}")
            raise

        result = await next_call(**kwargs)

        response = getattr(handler, "response", None)
        if response is not None:
            await update_all_token_counters(
                deployment_id, response, config, redis_client
            )

        return result

    return wrapper
