# Copyright 2026 ODYSS.AI AG
# SPDX-License-Identifier: Apache-2.0
#
# See the NOTICE file for attribution information.
#
# Author:
# Aleksander Bydłowski
# abydlowski@theodyss.ai
# ai@bydlow.ski
from typing import Any, Optional

from odyss_ai_flows.core.config.builder import build_config_tree
from odyss_ai_flows.core.config.context import _config_context, config, node_scope
from odyss_ai_flows.core.config.global_config import get_global_setting
from odyss_ai_flows.core.config.manager import ConfigManager
from odyss_ai_flows.core.config.resolver import resolve_config_async as _resolve_config_tree
from odyss_ai_flows.core.config.tree import ConfigNode


# ---------------------------------------------------------
# Initialization
# ---------------------------------------------------------

async def init_config_for_current_scope(
    *,
    provided_tree: Optional[dict] = None,
) -> None:
    """
    Initialize config manager for current execution context.

    Exactly one source is used:
    - provided_tree (preferred if given)
    - filesystem via build_config_tree()
    """

    if provided_tree is not None:
        root = ConfigNode.from_dict(provided_tree)
    else:
        root = await build_config_tree()

    instance = ConfigManager(root)
    _config_context.set(instance)

# ---------------------------------------------------------
# Public API
# ---------------------------------------------------------

async def cget(
    key: str,
    default: Optional[Any] = None,
    *,
    scope: Optional[str] = None
) -> Any:
    effective_scope = scope or node_scope.current

    if effective_scope is None:
        return await get_global_setting(key, default)

    return await config.get(
        key=key,
        default=default,
        node_scope=effective_scope,
    )


def set_node_scope(scope: str):
    return node_scope.set(scope)


def get_node_scope():
    return node_scope.current


def reset_node_scope(token):
    node_scope.reset(token)


async def pre_resolve_config_tree_async():
    await _resolve_config_tree(config)
    
    
    
    
    
