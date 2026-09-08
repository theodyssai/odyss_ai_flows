from __future__ import annotations

import json
import time
from enum import Enum
from functools import wraps
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Awaitable, Callable

from pydantic import BaseModel

from odyss_ai_flows.core.config.api import cget
from odyss_ai_flows.core.runtime.run_context import current_top_run_id
from odyss_ai_flows.core.utils.logger import logger

RunFn = Callable[..., Awaitable[Any]]


class CacheStrategy(str, Enum):
    BOTH = "both"
    WRITE = "write"
    WRITE_MANY = "write_many"
    NONE = "none"


_NON_SERIALIZABLE = "__non_serializable__"
_NAMESPACE = "__is_simplenamespace__"
_TUPLE = "__is_tuple__"


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

def _serialize(obj: Any) -> Any:
    if isinstance(obj, BaseModel):
        return _serialize(obj.model_dump())
    if isinstance(obj, SimpleNamespace):
        return {_NAMESPACE: True, **{k: _serialize(v) for k, v in vars(obj).items()}}
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize(v) for v in obj]
    if isinstance(obj, tuple):
        return {_TUPLE: True, "items": [_serialize(v) for v in obj]}
    try:
        json.dumps(obj)
        return obj
    except (TypeError, OverflowError):
        return {_NON_SERIALIZABLE: str(type(obj))}


def _deserialize(data: Any) -> Any:
    if isinstance(data, dict):
        if _NAMESPACE in data:
            return SimpleNamespace(
                **{k: _deserialize(v) for k, v in data.items() if k != _NAMESPACE}
            )
        if _TUPLE in data:
            return tuple(_deserialize(v) for v in data["items"])
        return {k: _deserialize(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_deserialize(v) for v in data]
    return data


def _has_marker(data: Any) -> bool:
    if isinstance(data, dict):
        return _NON_SERIALIZABLE in data or any(_has_marker(v) for v in data.values())
    if isinstance(data, list):
        return any(_has_marker(v) for v in data)
    return False


# ---------------------------------------------------------------------------
# Cache file location
# ---------------------------------------------------------------------------

_RUN_SUBDIRS: dict[str, str] = {}


def _run_subdir(run_id: str) -> str:
    name = _RUN_SUBDIRS.get(run_id)
    if name is None:
        name = f"{time.strftime('%Y%m%d_%H%M%S')}_{run_id[:8]}"
        _RUN_SUBDIRS[run_id] = name
    return name


def _cache_file(scope: str, base_dir: str, subdir: str | None) -> Path:
    root = Path(base_dir)
    if subdir:
        root = root / subdir
    path = root / Path(scope).with_suffix(".json")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

def cache_middleware(next_call: RunFn, handler) -> RunFn:
    @wraps(next_call)
    async def wrapper(**kwargs: Any) -> Any:
        cfg = await cget("cache", {}) or {}
        strategy = cfg.get("strategy", "none")

        if strategy == "none":
            return await next_call(**kwargs)

        scope = handler.node.scope
        subdir = None
        if strategy == "write_many":
            run_id = current_top_run_id() or "no_run_id"
            subdir = _run_subdir(run_id)
        cache_file = _cache_file(scope, cfg.get("dir", ".odyss_cache"), subdir)

        if strategy == "both" and cache_file.exists():
            try:
                cached = json.loads(cache_file.read_text())
                if _has_marker(cached):
                    logger.debug(f"[CACHE] {scope} unusable, re-running")
                else:
                    logger.debug(f"[CACHE] {scope} hit -> {cache_file}")
                    return _deserialize(cached)
            except Exception as exc:
                logger.warning(f"[CACHE] {scope} read failed: {exc}")

        result = await next_call(**kwargs)

        serialized = _serialize(result)
        if _has_marker(serialized):
            logger.debug(f"[CACHE] {scope} result not serializable, skipping write")
        else:
            try:
                cache_file.write_text(json.dumps(serialized))
                logger.debug(f"[CACHE] {scope} wrote -> {cache_file}")
            except Exception as exc:
                logger.warning(f"[CACHE] {scope} write failed: {exc}")

        return result

    return wrapper
