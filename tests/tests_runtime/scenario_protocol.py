# tests/tests_runtime/scenario_protocol.py

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Optional


# ---------------------------------------------------------
# Assertion contract
# ---------------------------------------------------------

AssertionFn = Callable[[Any], None]


# ---------------------------------------------------------
# Scenario runtime definition
# ---------------------------------------------------------

@dataclass(slots=True)
class ScenarioRuntimeDefinition:

    # -----------------------------------------------------
    # Required
    # -----------------------------------------------------

    flow: Any

    # -----------------------------------------------------
    # Optional runtime inputs
    # -----------------------------------------------------

    inputs: dict[str, Any] = field(
        default_factory=dict
    )

    variant_paths: list[Path] = field(
        default_factory=list
    )

    run_name: Optional[str] = None

    raise_on_fail: bool = False

    # -----------------------------------------------------
    # Assertions
    # -----------------------------------------------------

    assertions: list[AssertionFn] = field(
        default_factory=list
    )

    # -----------------------------------------------------
    # Optional metadata
    # -----------------------------------------------------

    metadata: dict[str, Any] = field(
        default_factory=dict
    )