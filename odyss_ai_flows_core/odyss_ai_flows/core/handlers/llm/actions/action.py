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

import inspect

from enum import Enum
from typing import Any, Callable
from pydantic import BaseModel


class ExecutorMode(Enum):
    MANY = "many"
    ONE = "one"
    ALL = "all"


class Action:
    def __init__(
        self,
        name: str,
        model: type[BaseModel],
        function: Callable,
        description: str | dict[str, str] = "",
        multi: bool = False,
    ):
        self.name = name
        self.model = model
        self.function = function
        self.description = description
        self.multi = multi

    async def execute(self, args: Any) -> Any:
        if inspect.iscoroutinefunction(self.function):
            return await self.function(args)

        return self.function(args)

    def get_description(self, mode: str = "default") -> str:
        if isinstance(self.description, str):
            return self.description

        if not self.description:
            return ""

        return (
            self.description.get(mode)
            or self.description.get("default")
            or next(iter(self.description.values()))
        )