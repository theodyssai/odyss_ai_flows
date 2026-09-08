# Copyright 2026 ODYSS.AI AG
# SPDX-License-Identifier: Apache-2.0
#
# See the NOTICE file for attribution information.
#
# Author:
# Aleksander Bydłowski
# abydlowski@theodyss.ai
# ai@bydlow.ski
# core/config/global_config.py

import json

from pathlib import Path
from typing import Any

from odyss_ai_flows.core.config.resolver import (
    resolve,
)


# ---------------------------------------------------------
# Raw global config repository
# ---------------------------------------------------------

_GLOBAL_CONFIG_PATH = Path("global_config.json")

_global_config_cache: dict[str, Any] = {}

_loaded = False


# ---------------------------------------------------------
# Internal loading
# ---------------------------------------------------------

def _load_global_config():

    global _global_config_cache
    global _loaded

    if _loaded:
        return

    if _GLOBAL_CONFIG_PATH.is_file():

        with open(
            _GLOBAL_CONFIG_PATH,
            "r",
            encoding="utf-8",
        ) as f:

            _global_config_cache = json.load(f)

    else:

        _global_config_cache = {}

    _loaded = True


# ---------------------------------------------------------
# Internal traversal
# ---------------------------------------------------------

def _traverse_key_path(
    root: dict,
    key: str,
    default: Any,
) -> Any:

    current = root

    for part in key.split("."):

        if not isinstance(
            current,
            dict,
        ):
            return default

        if part not in current:
            return default

        current = current[part]

    return current


# ---------------------------------------------------------
# Public API
# ---------------------------------------------------------

async def get_global_setting(
    key: str,
    default: Any = None,
) -> Any:
    """
    Lazy global config access.

    Global config remains:
    - raw
    - unresolved
    - process-global

    Resolution happens only when values are accessed.

    Global config intentionally:
    - supports dotted traversal
    - supports providers/Jinja
    - does NOT support REF semantics
    - does NOT support scoped merges
    """

    _load_global_config()

    raw = _traverse_key_path(
        _global_config_cache,
        key,
        default,
    )

    return await resolve(
        raw
    )


# ---------------------------------------------------------
# Optional eager pre-resolution
# ---------------------------------------------------------

async def pre_resolve_global_config_async():
    """
    Optional bootstrap optimization.

    Forces semantic compilation of all global
    config entries and warms semantic template cache.

    Does NOT mutate global config storage.
    """

    _load_global_config()

    for value in _global_config_cache.values():

        await resolve(
            value
        )


# ---------------------------------------------------------
# Optional helpers
# ---------------------------------------------------------

def get_raw_global_config() -> dict[str, Any]:
    """
    Returns raw unresolved global config repository.
    """

    _load_global_config()

    return _global_config_cache