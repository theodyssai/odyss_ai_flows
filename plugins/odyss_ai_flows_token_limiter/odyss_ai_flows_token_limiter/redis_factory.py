from __future__ import annotations

from typing import Any, Dict, Optional

from odyss_ai_flows.core.utils.logger import logger


_redis_client: Optional[Any] = None


async def get_redis_client(redis_config: Optional[Dict[str, Any]] = None) -> Any:
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    from redis.asyncio import Redis

    redis_config = redis_config or {}
    host = redis_config.get("host", "localhost")
    port = int(redis_config.get("port", 6379))

    if host == "localhost":
        _redis_client = Redis(host=host, port=port, decode_responses=True)
    else:
        access_key = redis_config.get("access_key")
        if not access_key:
            raise RuntimeError(
                "redis.access_key must be set in config for remote Redis connection"
            )
        _redis_client = Redis(
            host=host,
            port=port,
            password=access_key,
            ssl=True,
            decode_responses=True,
        )
        logger.info("Authenticated to Redis using access key.")

    await _redis_client.ping()
    return _redis_client


def set_redis_client(client: Any) -> None:
    """Inject a client (e.g. fakeredis) — primarily for tests."""
    global _redis_client
    _redis_client = client


def reset_redis_client() -> None:
    global _redis_client
    _redis_client = None
