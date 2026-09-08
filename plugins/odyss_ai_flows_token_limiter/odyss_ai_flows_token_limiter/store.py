from __future__ import annotations

import time
from typing import Any, Dict, Optional, Tuple

from odyss_ai_flows.core.utils.logger import logger


# =========================================================
# Redis-backed leaky-bucket counter store
# =========================================================

# Buckets live in Redis as hashes keyed "{direction}_tokens:{scope_id}:{window}"
# holding {used, last_updated}; each drains at limit / window_size per second.

WINDOW_SIZES: Dict[str, int] = {
    "second": 1,
    "minute": 60,
    "hour": 3600,
    "day": 86400,
    "week": 604800,
    "month": 2592000,
}

_DIRECTIONS = ("input", "output")

# evalsha registration: the update script is loaded once and its SHA cached in
# Redis so every process/worker shares the same script.
_SCRIPT_SHA_KEY = "token_limiter:script_sha"
_UPDATE_SCRIPT = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window_size = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local tokens = tonumber(ARGV[4])
local state = redis.call('HGETALL', key)
local used = 0
local last_updated = now
for i = 1, #state, 2 do
    if state[i] == 'used' then used = tonumber(state[i+1]) end
    if state[i] == 'last_updated' then last_updated = tonumber(state[i+1]) end
end
local elapsed = now - last_updated
local decay = (elapsed / window_size) * limit
used = math.max(used - decay, 0)
used = used + tokens
redis.call('HSET', key, 'used', used, 'last_updated', now)
return used
"""


class TokenLimitExceeded(Exception):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.details = details or {}


def _token_key(direction: str, scope_id: str, window: str) -> str:
    return f"{direction}_tokens:{scope_id}:{window}"


def _window_size_seconds(window: str) -> int:
    return WINDOW_SIZES.get(window, 1)


def _scopes(deployment_id: str) -> list[Tuple[str, str]]:
    return [("general", "general"), ("deployment", deployment_id)]


def get_token_usage_from_response(response: Any) -> Tuple[int, int]:
    usage = getattr(response, "usage", None)
    input_tokens = getattr(usage, "prompt_tokens", 0) or 0 if usage else 0
    output_tokens = getattr(usage, "completion_tokens", 0) or 0 if usage else 0
    return input_tokens, output_tokens


def _decayed_used(state: Dict[str, Any], limit: float, window: str, now: float) -> float:
    used = float(state.get("used", 0))
    last_updated = float(state.get("last_updated", now))
    elapsed = now - last_updated
    decay = (elapsed / _window_size_seconds(window)) * limit
    return max(used - decay, 0)


# =========================================================
# Preflight check
# =========================================================

async def raise_if_token_limit_exceeded(
    deployment_id: str,
    config: Dict[str, Any],
    redis_client: Any,
) -> None:
    soft_limit = config.get("soft_limit", False)

    pipeline = redis_client.pipeline()
    keys_info = []
    for direction in _DIRECTIONS:
        for scope_type, scope_id in _scopes(deployment_id):
            limits = config.get(scope_type, {}).get(direction, {})
            for window, limit in limits.items():
                key = _token_key(direction, scope_id, window)
                pipeline.hgetall(key)
                keys_info.append((direction, scope_type, scope_id, window, limit, key))

    results = await pipeline.execute()

    for (direction, scope_type, scope_id, window, limit, key), state in zip(
        keys_info, results
    ):
        used = float(state.get("used", 0))
        if used > float(limit):
            details = {
                "direction": direction,
                "scope_type": scope_type,
                "scope_id": scope_id,
                "window": window,
                "used": used,
                "limit": limit,
                "key": key,
            }
            if not soft_limit:
                raise TokenLimitExceeded(
                    f"Token limit exceeded for {direction} "
                    f"{scope_type} {scope_id} in window {window}",
                    details=details,
                )
            logger.warning(f"Soft token limit exceeded: {details}")


# =========================================================
# Post-call counter update (leak + increment)
# =========================================================

async def _get_script_sha(redis_client: Any) -> Optional[str]:
    sha = await redis_client.get(_SCRIPT_SHA_KEY)
    return sha.decode() if hasattr(sha, "decode") else sha


async def _register_script(redis_client: Any) -> str:
    sha = await redis_client.script_load(_UPDATE_SCRIPT)
    await redis_client.set(_SCRIPT_SHA_KEY, sha)
    logger.warning("Lua script for token limiter registered in Redis and SHA stored.")
    return sha


async def update_all_token_counters(
    deployment_id: str,
    response: Any,
    config: Dict[str, Any],
    redis_client: Any,
    now: Optional[float] = None,
) -> None:
    if now is None:
        now = time.time()

    input_tokens, output_tokens = get_token_usage_from_response(response)

    sha = await _get_script_sha(redis_client) or await _register_script(redis_client)

    def _build_pipeline(sha: str):
        pipeline = redis_client.pipeline()
        keys_info = []
        for direction, tokens in (("input", input_tokens), ("output", output_tokens)):
            for scope_type, scope_id in _scopes(deployment_id):
                limits = config.get(scope_type, {}).get(direction, {})
                for window, limit in limits.items():
                    key = _token_key(direction, scope_id, window)
                    window_size = _window_size_seconds(window)
                    pipeline.evalsha(sha, 1, key, now, window_size, limit, tokens)
                    keys_info.append((key, tokens))
        return pipeline, keys_info

    pipeline, keys_info = _build_pipeline(sha)
    try:
        results = await pipeline.execute()
    except Exception as e:
        logger.warning(f"Lua script SHA missing or failed, re-registering. Reason: {e}")
        sha = await _register_script(redis_client)
        pipeline, keys_info = _build_pipeline(sha)
        results = await pipeline.execute()

    for (key, tokens), used in zip(keys_info, results):
        logger.debug(f"Updated key: {key} with tokens: {tokens}, new used value: {used}")


# =========================================================
# Read-only views
# =========================================================

async def get_all_token_counters(
    deployment_id: str,
    config: Dict[str, Any],
    redis_client: Any,
    now: Optional[float] = None,
) -> Dict[str, Dict[str, Any]]:
    if now is None:
        now = time.time()

    pipeline = redis_client.pipeline()
    keys_info = []
    for direction in _DIRECTIONS:
        for scope_type, scope_id in _scopes(deployment_id):
            limits = config.get(scope_type, {}).get(direction, {})
            for window, limit in limits.items():
                pipeline.hgetall(_token_key(direction, scope_id, window))
                keys_info.append((direction, scope_type, scope_id, window, limit))

    results = await pipeline.execute()

    counters: Dict[str, Dict[str, Any]] = {"input": {}, "output": {}}
    for (direction, scope_type, scope_id, window, limit), state in zip(
        keys_info, results
    ):
        used = _decayed_used(state, float(limit), window, now)
        if scope_type == "general":
            counters[direction].setdefault(scope_type, {})[window] = used
        else:
            counters[direction].setdefault(scope_type, {}).setdefault(scope_id, {})[
                window
            ] = used

    return counters


async def get_tokens_left(
    deployment_id: str,
    config: Dict[str, Any],
    redis_client: Any,
) -> Dict[str, Dict[str, Any]]:
    counters = await get_all_token_counters(deployment_id, config, redis_client)
    tokens_left: Dict[str, Dict[str, Any]] = {"input": {}, "output": {}}

    for direction in _DIRECTIONS:
        for scope_type, scope_id in _scopes(deployment_id):
            limits = config.get(scope_type, {}).get(direction, {})
            if scope_type == "general":
                bucket = tokens_left[direction].setdefault(scope_type, {})
                for window, limit in limits.items():
                    used = counters[direction].get(scope_type, {}).get(window, 0)
                    bucket[window] = max(float(limit) - used, 0)
            else:
                bucket = tokens_left[direction].setdefault(scope_type, {}).setdefault(
                    scope_id, {}
                )
                for window, limit in limits.items():
                    used = (
                        counters[direction]
                        .get(scope_type, {})
                        .get(scope_id, {})
                        .get(window, 0)
                    )
                    bucket[window] = max(float(limit) - used, 0)

    return tokens_left


async def get_raw_token_counters(
    deployment_id: str,
    config: Dict[str, Any],
    redis_client: Any,
) -> Dict[str, Dict[str, Any]]:
    import datetime

    keys = []
    for direction in _DIRECTIONS:
        for scope_type, scope_id in _scopes(deployment_id):
            limits = config.get(scope_type, {}).get(direction, {})
            for window in limits.keys():
                keys.append(_token_key(direction, scope_id, window))

    pipeline = redis_client.pipeline()
    for key in keys:
        pipeline.hgetall(key)
    results = await pipeline.execute()

    counters: Dict[str, Dict[str, Any]] = {}
    for key, raw in zip(keys, results):
        formatted = dict(raw)
        if "last_updated" in raw:
            try:
                ts = float(raw["last_updated"])
                formatted["last_updated"] = datetime.datetime.fromtimestamp(ts).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            except Exception:
                pass
        counters[key] = formatted
    return counters


async def clean_all_token_counters(
    deployment_id: str,
    config: Dict[str, Any],
    redis_client: Any,
) -> None:
    now = time.time()
    pipeline = redis_client.pipeline()
    for direction in _DIRECTIONS:
        for scope_type, scope_id in _scopes(deployment_id):
            limits = config.get(scope_type, {}).get(direction, {})
            for window in limits.keys():
                key = _token_key(direction, scope_id, window)
                pipeline.hset(key, mapping={"used": 0, "last_updated": now})
                logger.debug(f"Cleaned token counter for key: {key}")
    await pipeline.execute()
