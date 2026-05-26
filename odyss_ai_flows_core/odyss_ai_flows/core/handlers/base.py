# Copyright 2026 ODYSS.AI AG
# SPDX-License-Identifier: Apache-2.0
#
# See the NOTICE file for attribution information.
#
# Author:
# Aleksander Bydłowski
# abydlowski@theodyss.ai
# aleksander.bydlowski@gmail.com
from abc import ABC, abstractmethod
from typing import Any
from odyss_ai_flows.core.config.api import set_node_scope
from odyss_ai_flows.core.handlers.middleware.middleware import apply_middleware
from odyss_ai_flows.core.builder.types import FlowNode


class AbstractHandler(ABC):
    def __init__(self, node: FlowNode):
        self.node = node

    async def run(self, **kwargs) -> Any:
        if not self.node:
            raise RuntimeError("Handler has not been bound to a node")

        set_node_scope(self.node.scope)

        middleware_wrapped = await apply_middleware(self._run, self)
        return await middleware_wrapped(**kwargs)

    @abstractmethod
    async def _run(self, **kwargs) -> Any:
        ...
