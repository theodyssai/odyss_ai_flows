# Copyright 2026 ODYSS.AI AG
# SPDX-License-Identifier: Apache-2.0
#
# See the NOTICE file for attribution information.
#
# Author:
# Aleksander Bydłowski
# abydlowski@theodyss.ai
# ai@bydlow.ski
# --- Exceptions ---


from pathlib import Path
from typing import List


class InvalidReferenceCompositionError(RuntimeError):
    """Raised when REF() is mixed with other providers or literals in one entry."""


class ConfigReferenceCycleError(RuntimeError):
    """Raised when REF() directives form a cycle in the config graph."""

    def __init__(self, chain: List[str]):

        self.chain = chain

        super().__init__(
            "Circular REF() reference detected in config graph: "
            + " -> ".join(chain)
        )


class ConfigMergeCycleError(RuntimeError):
    """Raised when ``$REF`` file-merge directives form a cycle."""

    def __init__(self, chain: List[Path]):

        self.chain = chain

        rendered = " -> ".join(str(p) for p in chain)

        super().__init__(
            f"Circular $REF detected in config merge chain: {rendered}"
        )
