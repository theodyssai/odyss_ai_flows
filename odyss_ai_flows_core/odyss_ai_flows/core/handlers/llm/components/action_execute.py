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

import traceback

from asyncio import TaskGroup
from typing import Any

from pydantic import BaseModel

from odyss_ai_flows.core.utils.logger import logger
from odyss_ai_flows.core.handlers.llm.actions.action import Action
from odyss_ai_flows.core.handlers.llm.actions.action import ExecutorMode
from odyss_ai_flows.core.handlers.llm.components.base import LLMHandlerComponent


class ActionExecuteComponent(LLMHandlerComponent):
    async def run(self, data: Any) -> Any:
        actions: list[Action] = getattr(
            self.handler,
            "actions",
            [],
        )

        if not actions:
            return data

        structured = getattr(
            self.handler,
            "structured",
            None,
        )

        if structured is None:
            raise RuntimeError(
                f"{self.handler.node.name} - actions were registered but "
                f"handler.structured is missing. A structured caller "
                f"component is required before action execution."
            )

        mode = getattr(
            self.handler,
            "action_mode",
            ExecutorMode.MANY,
        )

        if isinstance(mode, str):
            mode = ExecutorMode(mode)

        action_map = {
            action.name: action
            for action in actions
        }

        results: dict[str, Any] = {}

        async def run_action(
            action_name: str,
            arguments: Any,
        ):
            action = action_map[action_name]

            try:
                if action.multi:
                    results[action_name] = [
                        await action.execute(args)
                        for args in arguments
                    ]

                else:
                    results[action_name] = await action.execute(
                        arguments
                    )

            except Exception as e:
                logger.error(
                    f"Action '{action_name}' failed with error: {e}\n"
                    f"Full traceback:\n{traceback.format_exc()}"
                )

                results[action_name] = None

        if mode == ExecutorMode.ONE:
            await self._execute_one_mode(
                structured=structured,
                results=results,
                run_action=run_action,
            )

        elif mode == ExecutorMode.ALL:
            await self._execute_all_mode(
                structured=structured,
                action_map=action_map,
                results=results,
                run_action=run_action,
            )

        else:
            await self._execute_many_mode(
                structured=structured,
                action_map=action_map,
                results=results,
                run_action=run_action,
            )

        self.handler.action_results = results

        return results

    async def _execute_many_mode(
        self,
        structured: BaseModel,
        action_map: dict[str, Action],
        results: dict[str, Any],
        run_action,
    ) -> None:

        async with TaskGroup() as task_group:
            for action_name, action in action_map.items():

                request = getattr(
                    structured,
                    f"{action_name}_action_request",
                )

                should_execute = getattr(
                    request,
                    f"{action_name}_action_should_be_executed",
                )

                if not should_execute:
                    results[action_name] = None
                    continue

                arguments = getattr(
                    request,
                    _arguments_field_name(
                        action_name,
                        action.multi,
                    ),
                )

                task_group.create_task(
                    run_action(
                        action_name,
                        arguments,
                    )
                )

    async def _execute_all_mode(
        self,
        structured: BaseModel,
        action_map: dict[str, Action],
        results: dict[str, Any],
        run_action,
    ) -> None:

        async with TaskGroup() as task_group:
            for action_name, action in action_map.items():

                request = getattr(
                    structured,
                    f"{action_name}_required_action_request",
                )

                arguments = getattr(
                    request,
                    _arguments_field_name(
                        action_name,
                        action.multi,
                    ),
                )

                task_group.create_task(
                    run_action(
                        action_name,
                        arguments,
                    )
                )

    async def _execute_one_mode(
        self,
        structured: BaseModel,
        results: dict[str, Any],
        run_action,
    ) -> None:

        selected = getattr(
            structured,
            "selected_action_for_execution",
        )

        action_name = getattr(
            selected,
            "selected_action_name_for_execution",
        )

        action = next(
            action
            for action in self.handler.actions
            if action.name == action_name
        )

        arguments = getattr(
            selected,
            _arguments_field_name(
                action_name,
                action.multi,
            ),
        )

        await run_action(
            action_name,
            arguments,
        )


def _arguments_field_name(
    action_name: str,
    multi: bool,
) -> str:

    if multi:
        return (
            f"{action_name}_action_calls_to_execute"
        )

    return (
        f"{action_name}_action_arguments"
    )