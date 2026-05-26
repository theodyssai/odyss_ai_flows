# tests/tests_runtime/models.py

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


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
            if not r.success
        )

    @property
    def success(self) -> bool:
        return self.failed == 0
    
@dataclass(slots=True)
class ScenarioError:

    type: str

    message: str

    traceback: str