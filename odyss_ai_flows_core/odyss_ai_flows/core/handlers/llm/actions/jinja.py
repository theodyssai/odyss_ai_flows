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

from collections.abc import Iterable

from odyss_ai_flows.core.handlers.llm.actions.action import Action
from odyss_ai_flows.core.handlers.llm.actions.action import ExecutorMode
from odyss_ai_flows.core.handlers.llm.actions.rendering import render_actions


def flatten_actions(items) -> list[Action]:
    result: list[Action] = []

    for item in items:
        if item is None:
            continue

        if isinstance(item, Action):
            result.append(item)
            continue

        if isinstance(item, Iterable) and not isinstance(item, (str, bytes)):
            result.extend(flatten_actions(item))
            continue

        raise TypeError(
            f"Unsupported action object type: {type(item)}"
        )

    return result


def make_actions_func(handler):
    def actions(
        *items,
        mode: ExecutorMode | str = ExecutorMode.MANY,
        render_mode: str = "default",
    ) -> str:

        resolved_actions = flatten_actions(items)

        if isinstance(mode, str):
            mode = ExecutorMode(mode)

        if not hasattr(handler, "actions"):
            handler.actions = []

        handler.actions.extend(resolved_actions)

        handler.action_mode = mode
        handler.action_render_mode = render_mode

        return render_actions(
            resolved_actions,
            mode=mode,
            render_mode=render_mode,
        )

    return actions