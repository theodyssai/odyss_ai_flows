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

from typing import Iterable

from odyss_ai_flows.core.handlers.llm.actions.action import Action
from odyss_ai_flows.core.handlers.llm.actions.action import ExecutorMode


def render_actions(
    actions: Iterable[Action],
    mode: ExecutorMode | str = ExecutorMode.MANY,
    render_mode: str = "default",
) -> str:

    if isinstance(mode, ExecutorMode):
        mode_value = mode.value
    else:
        mode_value = mode

    lines: list[str] = []

    lines.append("Available actions:")
    lines.append("")

    for idx, action in enumerate(actions, start=1):
        lines.append(f"{idx}. {action.name}")

        description = action.get_description(render_mode)
        if description:
            lines.append(f"Description: {description}")

        if action.multi:
            lines.append(
                "This action can be called multiple times."
            )

        model = action.model

        fields = getattr(model, "model_fields", {})

        if fields:
            lines.append("Arguments:")

            for field_name, field_info in fields.items():
                annotation = field_info.annotation

                annotation_name = getattr(
                    annotation,
                    "__name__",
                    str(annotation),
                )

                field_description = ""

                if getattr(field_info, "description", None):
                    field_description = f" - {field_info.description}"

                lines.append(
                    f"- {field_name}: {annotation_name}{field_description}"
                )

        lines.append("")

    if mode_value == ExecutorMode.ONE.value:
        lines.append(
            "You must choose exactly one action."
        )

    elif mode_value == ExecutorMode.MANY.value:
        lines.append(
            "You may choose multiple actions."
        )

    elif mode_value == ExecutorMode.ALL.value:
        lines.append(
            "You must provide arguments for all actions."
        )

    return "\n".join(lines).strip()