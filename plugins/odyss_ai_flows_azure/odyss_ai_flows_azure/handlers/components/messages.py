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
from typing import Optional, List, TYPE_CHECKING

from odyss_ai_flows.core.handlers.llm.components.base import LLMHandlerComponent

if TYPE_CHECKING:
    from odyss_ai_flows.core.handlers.llm.composed_handler import ComposedHandler


class MessageBuilderBase(LLMHandlerComponent):
    def __init__(self, handler: 'ComposedHandler', system_fallback: str = "You are a helpful assistant."):
        super().__init__(handler)
        self.system_fallback = system_fallback

    def _system_msg(self) -> dict:
        return {"role": "system", "content": self.system_fallback}

    def _user_parts(self, text: str) -> list[dict]:
        parts: list[dict] = []
        t = text.strip()
        if t:
            parts.append({"type": "text", "text": t})
        for img in self.handler.image_segments:
            parts.append(
                {"type": "image_url", "image_url": {"url": img["image"]}})
        return parts


class SimpleMessageBuilder(MessageBuilderBase):
    async def run(self, data: Optional[str]) -> str:
        raw = (data or "").strip()
        self.handler.messages = [
            self._system_msg(),
            {"role": "user", "content": self._user_parts(raw)},
        ]
        return raw


class RoleMessageBuilder(MessageBuilderBase):
    async def run(self, data: Optional[str]) -> str:
        raw = data or ""
        lines = raw.splitlines()
        messages: List[dict] = []
        current = {"role": None, "content": []}

        for line in lines:
            s = line.strip()
            if s.startswith("@role("):
                if current["role"] and any(x.strip() for x in current["content"]):
                    messages.append(
                        {"role": current["role"], "content": "\n".join(current["content"]).strip()})
                role = s[6:].rstrip(")").strip("'\" ")
                current = {"role": role, "content": []}
            else:
                current["content"].append(line)

        if current["role"] and any(x.strip() for x in current["content"]):
            messages.append(
                {"role": current["role"], "content": "\n".join(current["content"]).strip()})

        if not messages:
            self.handler.messages = [
                self._system_msg(),
                {"role": "user", "content": self._user_parts(raw)},
            ]
            return raw

        final_messages: list[dict] = []
        for m in messages:
            if m["role"] == "user":
                final_messages.append(
                    {"role": "user", "content": self._user_parts(m["content"])})
            else:
                final_messages.append(
                    {"role": m["role"], "content": m["content"]})
        self.handler.messages = final_messages
        return raw
