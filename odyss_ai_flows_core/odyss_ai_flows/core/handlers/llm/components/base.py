# Copyright 2026 ODYSS.AI AG
# SPDX-License-Identifier: Apache-2.0
#
# See the NOTICE file for attribution information.
#
# Author:
# Aleksander Bydłowski
# abydlowski@theodyss.ai
# ai@bydlow.ski

from __future__ import annotations
from typing import Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from odyss_ai_flows.core.handlers.llm.composed_handler import ComposedHandler


class LLMHandlerComponent:
    def __init__(self, handler: 'ComposedHandler'):
        self.handler = handler

    async def run(self, data: Optional[str]) -> Any:
        raise NotImplementedError


