# Copyright 2026 ODYSS.AI AG
# SPDX-License-Identifier: Apache-2.0
#
# See the NOTICE file for attribution information.
#
# Author:
# Aleksander Bydłowski
# abydlowski@theodyss.ai
# aleksander.bydlowski@gmail.com
from __future__ import annotations
from typing import Optional

from odyss_ai_flows.core.utils.logger import logger
from odyss_ai_flows.core.handlers.llm.components.base import LLMHandlerComponent


class FinishReasonLogger(LLMHandlerComponent):
    async def run(self, data: Optional[str]) -> Optional[str]:
        resp = getattr(self.handler, "response", None)
        finish_reason = None

        if resp is not None and getattr(resp, "choices", None):
            finish_reason = resp.choices[0].finish_reason

        logger.info(
            f"{self.handler.node.name} - Finish reason: {finish_reason}")
        return data
