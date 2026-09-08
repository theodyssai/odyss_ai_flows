# Copyright 2026 ODYSS.AI AG
# SPDX-License-Identifier: Apache-2.0
#
# See the NOTICE file for attribution information.
# core/handlers/llm/connection.py
"""Shared resolution of the active LLM connection profile.

Every LLM provider plugin picks its connection settings the same way, so the
logic lives here once. 
"""

from __future__ import annotations

from typing import Any, Dict

from odyss_ai_flows.core.config.api import cget
from odyss_ai_flows.core.config.profiles import select_profile


LLM_CONFIG_KEY = "llm_config"
LLM_SELECTOR_KEY = "llm_connection_name"
LEGACY_SELECTOR_KEY = "oai_connection_name"


async def resolve_llm_connection(
    *,
    legacy_default: str = "azure_openai",
) -> Dict[str, Any]:
    registry = await cget(LLM_CONFIG_KEY, default=None)
    if registry:
        selector = await cget(LLM_SELECTOR_KEY, default=None)
        if selector is None:
            selector = await cget(LEGACY_SELECTOR_KEY, default=None)
        _name, cfg = select_profile(
            registry,
            selector,
            config_label=LLM_CONFIG_KEY,
            selector_label=LLM_SELECTOR_KEY,
        )
        return cfg

    key = await cget(LEGACY_SELECTOR_KEY, default=legacy_default)
    return await cget(key, default={}) or {}
