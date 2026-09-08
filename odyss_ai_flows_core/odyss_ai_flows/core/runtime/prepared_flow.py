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

from pathlib import Path
from typing import Any, List, Optional, Tuple, Union

# Avoid hard dependency import cycles via TYPE_CHECKING
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from odyss_ai_flows.core.files.repository import FileRepository


PathLike = Union[str, Path]
FsetValue = Any  # intentionally loose: str | Callable | Path (validated later)


class PreparedFlow:
    """
    Deferred flow definition based on repository mutations.

    This class does NOT:
    - construct repository eagerly
    - define nodes or structure
    - bypass existing builder/executor

    It ONLY:
    - records fset operations
    - applies them to a repository inside run_flow

    Design goals:
    - minimal boilerplate
    - no duplicate flow representation
    - full compatibility with filesystem + hybrid flows
    """

    __slots__ = ("base_path", "config_tree", "_fsets")

    def __init__(
        self,
        *,
        base_path: Optional[PathLike] = None,
        config_tree: Optional[dict] = None,
    ) -> None:
        self.base_path: Optional[Path] = Path(base_path) if base_path else None
        self.config_tree: Optional[dict] = config_tree

        # list of (rebased_path, value)
        self._fsets: List[Tuple[Path, FsetValue]] = []

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------

    def fset(self, path: PathLike, value: FsetValue) -> PreparedFlow:
        """
        Register a deferred repository mutation.

        Parameters:
            path:
                Virtual/rebased path within the flow.

            value:
                One of:
                - str (source code or template)
                - callable (python node)
                - Path (redirect to external file)

        Returns:
            self (for chaining)
        """
        self._fsets.append((Path(path), value))
        return self

    # ---------------------------------------------------------------------
    # Runtime integration (called by runner)
    # ---------------------------------------------------------------------

    def apply(self, repo: FileRepository) -> None:
        """
        Apply all deferred mutations to a repository.

        This must ONLY be called inside run_flow, after repo is initialized.
        """
        for path, value in self._fsets:

            if self.base_path is not None:

                final_path = (
                    self.base_path / path
                )

            else:

                final_path = path

            repo.fset(
                final_path,
                value,
            )

    # ---------------------------------------------------------------------
    # Introspection / debugging (optional but useful)
    # ---------------------------------------------------------------------

    def get_fsets(self) -> List[Tuple[Path, FsetValue]]:
        """
        Return a shallow copy of registered mutations.
        """
        return list(self._fsets)

    def __repr__(self) -> str:
        base = f"base_path={self.base_path!s}" if self.base_path else "base_path=None"
        cfg = "config=yes" if self.config_tree else "config=no"
        return f"<PreparedFlow {base}, fsets={len(self._fsets)}, {cfg}>"