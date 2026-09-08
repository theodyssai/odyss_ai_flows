# Copyright 2026 ODYSS.AI AG
# SPDX-License-Identifier: Apache-2.0
#
# See the NOTICE file for attribution information.
#
# Author:
# Aleksander Bydłowski
# abydlowski@theodyss.ai
# ai@bydlow.ski
import inspect
import importlib.util
from typing import Callable, Optional
from pathlib import Path

from odyss_ai_flows.core.handlers.base import AbstractHandler
from odyss_ai_flows.core.builder.types import FlowNode
from odyss_ai_flows.core.utils.logger import logger


class PythonHandler(AbstractHandler):
    def __init__(self, node: FlowNode):
        super().__init__(node)
        self.function: Optional[Callable] = None
        self._resolve_function()

    # ---------------------------------------------------------
    # Resolution entry point
    # ---------------------------------------------------------

    def _resolve_function(self):
        # --- CASE 1: callable provided directly ---
        if self.node.callable_obj is not None:
            self.function = self.node.callable_obj
            logger.debug(
                f"[PythonHandler] Using callable_obj for node '{self.node.name}'"
            )
            return

        # --- CASE 2: code string (content) ---
        if self.node.content is not None:
            self._load_from_content(self.node.content)
            return

        # --- CASE 3: path-based (filesystem / redirected) ---
        if self.node.path is not None:
            self._load_from_path(self.node.path)
            return

        # --- FAILURE ---
        raise RuntimeError(
            f"PythonHandler: node '{self.node.name}' has no executable source"
        )

    # ---------------------------------------------------------
    # Content-based resolution (exec)
    # ---------------------------------------------------------

    def _load_from_content(self, content: str):
        try:
            namespace: dict[str, object] = {}

            exec(content, namespace)

            candidates = [
                (name, obj)
                for name, obj in namespace.items()
                if callable(obj)
            ]

            if not candidates:
                raise RuntimeError(
                    f"No callable found in content for node '{self.node.name}'"
                )

            node_func = next(
                (f for f in candidates if getattr(f[1], "is_node", False)),
                None,
            )

            name, func = node_func if node_func else candidates[0]

            self.function = func

            logger.debug(
                f"[PythonHandler] Resolved function '{name}' from content "
                f"for node '{self.node.name}'"
            )

        except Exception as e:
            raise RuntimeError(
                f"Failed to execute content for node '{self.node.name}'"
            ) from e

    # ---------------------------------------------------------
    # Path-based resolution (importlib)
    # ---------------------------------------------------------

    def _load_from_path(self, path: Path):
        module_name = path.stem

        try:
            spec = importlib.util.spec_from_file_location(module_name, path)
            if spec is None or spec.loader is None:
                raise ImportError(f"Could not load spec from {path}")

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            file_here = Path(module.__file__).resolve()

            # --- strict: functions defined in THIS file ---
            candidates = [
                (name, obj)
                for name in dir(module)
                for obj in [getattr(module, name)]
                if inspect.isfunction(obj)
                and Path(obj.__code__.co_filename).resolve() == file_here
            ]

            # --- fallback: any callable ---
            if not candidates:
                candidates = [
                    (name, getattr(module, name))
                    for name in dir(module)
                    if callable(getattr(module, name))
                ]

            node_func = next(
                (f for f in candidates if getattr(f[1], "is_node", False)),
                None,
            )

            name, func = node_func if node_func else candidates[0]

            self.function = func

            logger.debug(
                f"[PythonHandler] Resolved function '{name}' from path '{path}' "
                f"for node '{self.node.name}'"
            )

        except Exception as e:
            raise RuntimeError(
                f"Failed to parse Python file '{path}' for node '{self.node.name}'"
            ) from e

    # ---------------------------------------------------------
    # Execution
    # ---------------------------------------------------------

    async def _run(self, **kwargs):
        if not self.function:
            raise RuntimeError("Function not properly resolved")

        if inspect.iscoroutinefunction(self.function):
            return await self.function()
        else:
            return self.function()