# tests/tests_runtime/models.py

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from tests.tests_runtime.requirements import (
    Requirement,
)


# ---------------------------------------------------------
# Discovery
# ---------------------------------------------------------

@dataclass(slots=True)
class ScenarioDefinition:

    id: str

    name: str

    group: str | None

    relative_path: Path

    path: Path

    scenario_file: Path

    requirements: list[Requirement] = field(
        default_factory=list
    )

    @property
    def requires_llm(self) -> bool:
        """Backward-compatible: has any runtime requirement."""

        return bool(self.requirements)


# ---------------------------------------------------------
# Execution result
# ---------------------------------------------------------

@dataclass(slots=True)
class ScenarioResult:
    scenario: ScenarioDefinition

    success: bool

    duration_seconds: float

    result: Any = None

    error: Optional[ScenarioError] = None

    logs_path: Optional[Path] = None

    skipped: bool = False

    skip_reason: Optional[str] = None


# ---------------------------------------------------------
# Suite result
# ---------------------------------------------------------

@dataclass(slots=True)
class SuiteResult:
    started_at: str

    finished_at: str

    duration_seconds: float

    scenario_results: list[ScenarioResult] = field(
        default_factory=list
    )

    @property
    def total(self) -> int:
        return len(self.scenario_results)

    @property
    def passed(self) -> int:
        return sum(
            1
            for r in self.scenario_results
            if r.success
        )

    @property
    def failed(self) -> int:
        return sum(
            1
            for r in self.scenario_results
            if not r.success and not r.skipped
        )

    @property
    def skipped(self) -> int:
        return sum(
            1
            for r in self.scenario_results
            if r.skipped
        )

    @property
    def success(self) -> bool:
        return self.failed == 0
    
@dataclass(slots=True)
class ScenarioError:

    type: str

    message: str

    traceback: str