# Copyright 2026 ODYSS.AI AG
# SPDX-License-Identifier: Apache-2.0
#
# See the NOTICE file for attribution information.
#
# Author:
# Aleksander Bydłowski
# abydlowski@theodyss.ai
# ai@bydlow.ski
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from odyss_ai_flows.core.handlers.base import AbstractHandler


from odyss_ai_flows.core.files.repository import FileEntry


@dataclass
class FlowNode:
    entry: FileEntry
    handler: Optional["AbstractHandler"] = field(default=None)

    # ---------------------------------------------------------
    # Transparent compatibility layer
    # ---------------------------------------------------------

    @property
    def name(self) -> str:
        assert self.entry.name is not None
        return self.entry.name

    @property
    def kind(self) -> str:
        # entry.kind = "node:python" → "python"
        return self.entry.kind.split(":", 1)[1]

    @property
    def path(self) -> Optional[Path]:
        """
        Backward-compatible:
        previously node.path was always real_path.

        Now:
        - redirected_path takes precedence
        - fallback to real_path
        - None for virtual-only nodes
        """
        if self.entry.redirected_path:
            return self.entry.redirected_path
        return self.entry.real_path

    @property
    def scope(self) -> str:
        """
        Same logic as before:
        derived from rebased_path
        """
        return str(self.entry.rebased_path.with_suffix(""))

    # ---------------------------------------------------------
    # New capabilities (used by new subsystems)
    # ---------------------------------------------------------

    @property
    def callable_obj(self):
        return self.entry.callable_obj

    @property
    def content(self):
        return self.entry.content

@dataclass
class FlowStructure:
    nodes: dict[str, FlowNode]
    base_path: Path
