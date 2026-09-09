from __future__ import annotations
from typing import Optional

from odyss_ai_flows.core.utils.logger import logger
from odyss_ai_flows.core.handlers.llm.components.base import LLMHandlerComponent


class TokenCounter(LLMHandlerComponent):
    async def run(self, data: Optional[str]) -> Optional[str]:
        resp = getattr(self.handler, "response", None)
        usage = getattr(resp, "usage", None) if resp is not None else None

        prompt = getattr(usage, "prompt_tokens",
                         None) if usage is not None else None
        completion = getattr(usage, "completion_tokens",
                             None) if usage is not None else None

        logger.info(
            f"{self.handler.node.name} - Tokens used: prompt={prompt}, response={completion}"
        )
        return data
