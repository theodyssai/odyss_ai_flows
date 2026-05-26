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

from typing import Any

from odyss_ai_flows.core.handlers.llm.actions.action import (
    ExecutorMode,
)

from odyss_ai_flows.core.handlers.llm.actions.model_builder import (
    build_actions_model,
)

from odyss_ai_flows.core.handlers.llm.components.base import (
    LLMHandlerComponent,
)


class ActionModelComponent(LLMHandlerComponent):
    async def run(self, data: Any) -> Any:

        actions = getattr(
            self.handler,
            "actions",
            None,
        )

        if not actions:
            return data

        # -----------------------------------------------------
        # Conflict detection
        # -----------------------------------------------------

        if getattr(
            self.handler,
            "static_model_class",
            None,
        ) is not None:

            raise RuntimeError(
                f"{self.handler.node.name} - "
                f"actions() cannot be used because "
                f"a node:model structured output "
                f"is already defined"
            )

        if getattr(
            self.handler,
            "dynamic_model_class",
            None,
        ) is not None:

            raise RuntimeError(
                f"{self.handler.node.name} - "
                f"actions() cannot be used because "
                f"model() already defined a "
                f"structured output model"
            )

        # -----------------------------------------------------
        # Resolve execution mode
        # -----------------------------------------------------

        mode = getattr(
            self.handler,
            "action_mode",
            ExecutorMode.MANY,
        )

        if isinstance(mode, str):
            mode = ExecutorMode(mode)

        # -----------------------------------------------------
        # Build dynamic action model
        # -----------------------------------------------------

        action_model_class = build_actions_model(
            actions=list(actions),
            mode=mode,
        )

        self.handler.action_model_class = (
            action_model_class
        )

        self.handler.model_class = (
            action_model_class
        )

        return data