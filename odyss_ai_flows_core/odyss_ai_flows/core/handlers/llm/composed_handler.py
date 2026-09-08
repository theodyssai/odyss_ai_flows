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

import importlib.util
import sys

from types import ModuleType
from typing import Any
from typing import Optional

from odyss_ai_flows.core.builder.types import FlowNode
from odyss_ai_flows.core.config.api import cget
from odyss_ai_flows.core.files.api import fget
from odyss_ai_flows.core.handlers.base import AbstractHandler
from odyss_ai_flows.core.handlers.llm.actions.action import ExecutorMode
from odyss_ai_flows.core.handlers.llm.components.base import (
    LLMHandlerComponent,
)
from odyss_ai_flows.core.handlers.llm.pipelines import (
    resolve_pipeline,
)
from odyss_ai_flows.core.handlers.llm.registry import (
    resolve_component_class,
)
from odyss_ai_flows.core.utils.logger import (
    logger,
)


class ComposedHandler(AbstractHandler):
    def __init__(self, node: FlowNode):
        super().__init__(node)

        self.node = node

        # ---------------------------------------------------------
        # Core runtime state
        # ---------------------------------------------------------

        self.messages: list[dict] = []
        self.image_segments: list[dict] = []

        self.rendered_text: str = ""

        self.response: Optional[object] = None

        # ---------------------------------------------------------
        # Structured output state
        # ---------------------------------------------------------

        self.model_class = None
        self.structured = None

        # ---------------------------------------------------------
        # Action system state
        # ---------------------------------------------------------

        self.actions = []

        self.action_mode = ExecutorMode.MANY
        self.action_render_mode = "default"

        self.action_model_class = None
        self.action_results = None

        # ---------------------------------------------------------
        # Internal state
        # ---------------------------------------------------------

        self._components: list[
            LLMHandlerComponent
        ] = []

        self._built = False
        self._skipped = False
        
        self.static_model_class = None
        self.dynamic_model_class = None
        self.action_model_class = None

    async def build(self) -> None:
        if self._built:
            return

        # ---------------------------------------------------------
        # Load node:model
        # ---------------------------------------------------------

        entry = fget(
            "node:model",
            name=self.node.name,
        )

        if entry:
            module = self._load_model_module(
                entry
            )

            for attr in dir(module):
                obj = getattr(module, attr)

                if getattr(
                    obj,
                    "_is_top_model",
                    False,
                ):
                    self.static_model_class = obj
                    self.model_class = obj
                    break

            if not self.model_class:
                raise RuntimeError(
                    f"No @model-decorated class "
                    f"found for node "
                    f"'{self.node.name}'"
                )

        # ---------------------------------------------------------
        # Resolve pipeline
        # ---------------------------------------------------------

        pipeline = await cget(
            "llm.pipeline",
            default=None,
        )

        user_pipelines = await cget(
            "llm.pipelines",
            default={},
        )

        effective_name, keys = resolve_pipeline(
            pipeline_name=pipeline,
            model_present=bool(
                self.model_class
            ),
            user_pipelines=user_pipelines,
        )

        logger.debug(
            f"{self.node.name} - "
            f"pipeline={effective_name} "
            f"-> {keys}"
        )

        self._components = [
            resolve_component_class(k)(self)
            for k in keys
        ]

        self._built = True

    async def _run(self) -> Any:
        await self.build()

        data: Optional[str] = None

        for comp in self._components:
            data = await comp.run(data)

            if self._skipped:
                logger.debug(
                    f"Node '{self.node.name}' "
                    f"skipped via skip()"
                )

                return None

        if self.action_results is not None:
            return self.action_results

        if self.structured is not None:
            return self.structured

        return data

    # ---------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------

    def _load_model_module(
        self,
        entry,
    ) -> ModuleType:

        # --- callable ---

        if entry.callable_obj is not None:
            module = ModuleType(
                "model_module"
            )

            setattr(
                module,
                entry.callable_obj.__name__,
                entry.callable_obj,
            )

            return module

        # --- content ---

        if entry.content is not None:
            module = ModuleType(
                "model_module"
            )

            exec(
                entry.content,
                module.__dict__,
            )

            return module

        # --- redirected path ---

        if entry.redirected_path is not None:
            return self._load_module_from_path(
                entry.redirected_path
            )

        # --- real path ---

        if entry.real_path is not None:
            return self._load_module_from_path(
                entry.real_path
            )

        raise RuntimeError(
            f"Invalid node:model entry "
            f"for node '{self.node.name}'"
        )

    def _load_module_from_path(
        self,
        path,
    ) -> ModuleType:

        spec = (
            importlib.util
            .spec_from_file_location(
                "model_module",
                str(path),
            )
        )

        if (
            spec is None
            or spec.loader is None
        ):
            raise RuntimeError(
                f"Could not load module "
                f"from {path}"
            )

        module = (
            importlib.util
            .module_from_spec(spec)
        )

        sys.modules[
            "model_module"
        ] = module

        spec.loader.exec_module(module)

        return module