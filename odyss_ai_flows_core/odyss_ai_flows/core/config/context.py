# Copyright 2026 ODYSS.AI AG
# SPDX-License-Identifier: Apache-2.0
#
# See the NOTICE file for attribution information.
#
# Author:
# Aleksander Bydłowski
# abydlowski@theodyss.ai
# aleksander.bydlowski@gmail.com
from contextvars import ContextVar
from typing import Optional

from odyss_ai_flows.core.config.manager import ConfigManager


_config_context: ContextVar[ConfigManager] = ContextVar("config_context")
_node_scope_context: ContextVar[Optional[str]] = ContextVar(
    "node_scope_context", default=None)


class ConfigProxy:
    def __getattr__(self, item):
        return getattr(_config_context.get(), item)


class NodeScopeProxy:
    @property
    def current(self) -> Optional[str]:
        return _node_scope_context.get()


    def set(self, scope: str):
        return _node_scope_context.set(scope)

    def reset(self, token):
        _node_scope_context.reset(token)


config = ConfigProxy()
node_scope = NodeScopeProxy()
