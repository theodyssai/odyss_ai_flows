# Copyright 2026 ODYSS.AI AG
# SPDX-License-Identifier: Apache-2.0
#
# See the NOTICE file for attribution information.
#
# Author:
# Aleksander Bydłowski
# abydlowski@theodyss.ai
# aleksander.bydlowski@gmail.com
# --- Exceptions ---


from odyss_ai_flows.core.runtime.run_context import get_run_name


class NodeExecutionError(Exception):
    def __init__(self, node_scope: str, original: BaseException, run_name: str | None = None):
        self.node_scope = node_scope
        self.original = original
        self.run_name = run_name or get_run_name()
        msg = f"[{self.run_name}] Node '{node_scope}' failed: {original!r}"
        super().__init__(msg)


class FrameworkError(Exception):
    def __init__(self, original: BaseException, run_name: str | None = None):
        self.original = original
        self.run_name = run_name or get_run_name()
        msg = f"[{self.run_name}] Framework error: {original!r}"
        super().__init__(msg)


class CycleDetectedError(FrameworkError):
    def __init__(self, path: list[str], run_name: str | None = None):
        self.path = path
        message = " -> ".join(path)
        super().__init__(RuntimeError(f"Dependency cycle detected: {message}"), run_name)


class FlowBreak(Exception):
    def __init__(self, message: str | None = None, run_name: str | None = None):
        super().__init__(message)
        self.message = message
        self.node_scope: str | None = None
        self.run_name: str = run_name or get_run_name()

    def __str__(self) -> str:
        base = self.message if self.message else "Flow break"
        scope_info = f" (scope: {self.node_scope})" if self.node_scope else ""
        return f"[{self.run_name}] {base}{scope_info}"

    def __repr__(self) -> str:
        cls = self.__class__.__name__
        base = self.message if self.message else "Flow break"
        scope_info = f", node_scope={self.node_scope!r}" if self.node_scope else ""
        return f"{cls}({base!r}{scope_info})"