from __future__ import annotations

import os
import subprocess

from dataclasses import dataclass
from importlib.metadata import (
    PackageNotFoundError,
    distribution,
)
from pathlib import Path

from tests.tests_runtime.requirements.base import (
    CONFIG_AXIS,
    ENV_LOCAL_FILENAME,
    PLUGIN_AXIS,
    PROVIDER_ENTRY_POINT_GROUPS,
    CheckFn,
    Requirement,
    RequirementStatus,
)

from tests.tests_runtime.requirements._helpers import (
    entry_points_for,
    invoke_check,
    normalise_check_result,
    read_env_local,
)


# ---------------------------------------------------------
# Plugin axis
# ---------------------------------------------------------

@dataclass(slots=True)
class PluginRequirement(Requirement):
    """A specific installed plugin, targeted by distribution name."""

    axis = PLUGIN_AXIS

    dist: str

    entry_point: str | None = None

    group: str | None = None

    def describe(self) -> str:
        if self.entry_point:
            return (
                f"plugin '{self.dist}' "
                f"(entry point '{self.entry_point}')"
            )

        return f"plugin '{self.dist}'"

    def check(
        self,
        scenario_dir: Path,
    ) -> RequirementStatus:

        try:
            distribution(self.dist)

        except PackageNotFoundError:
            return RequirementStatus(
                satisfied=False,
                detail=f"{self.dist} not installed",
            )

        if self.entry_point is None:
            return RequirementStatus(
                satisfied=True,
                detail=f"{self.dist} installed",
            )

        groups = (
            (self.group,)
            if self.group
            else PROVIDER_ENTRY_POINT_GROUPS
        )

        present = any(
            ep.name == self.entry_point
            for group in groups
            for ep in entry_points_for(group)
        )

        if present:
            return RequirementStatus(
                satisfied=True,
                detail=(
                    f"{self.dist} provides "
                    f"'{self.entry_point}'"
                ),
            )

        return RequirementStatus(
            satisfied=False,
            detail=(
                f"{self.dist} installed but "
                f"'{self.entry_point}' not registered"
            ),
        )


@dataclass(slots=True)
class AnyProviderRequirement(Requirement):
    """Any LLM-handling plugin. Tier 2 — borderline, discouraged.

    Prefer a specific PluginRequirement. This exists only for the
    rare scenario that genuinely works with any provider.
    """

    axis = PLUGIN_AXIS

    def describe(self) -> str:
        return "any LLM provider plugin"

    def check(
        self,
        scenario_dir: Path,
    ) -> RequirementStatus:

        present = any(
            entry_points_for(group)
            for group in PROVIDER_ENTRY_POINT_GROUPS
        )

        if present:
            return RequirementStatus(
                satisfied=True,
                detail="a provider plugin is installed",
            )

        return RequirementStatus(
            satisfied=False,
            detail="no provider plugin installed",
        )


# ---------------------------------------------------------
# Config axis
# ---------------------------------------------------------

@dataclass(slots=True)
class EnvRequirement(Requirement):
    """Environment variables, optionally read from .env.local too."""

    axis = CONFIG_AXIS

    vars: tuple[str, ...]

    consult_env_local: bool = True

    def describe(self) -> str:
        return f"env {list(self.vars)}"

    def check(
        self,
        scenario_dir: Path,
    ) -> RequirementStatus:

        local_values: dict[str, str] = {}

        if self.consult_env_local:
            local_values = read_env_local(
                scenario_dir / ENV_LOCAL_FILENAME
            )

        missing = [
            var
            for var in self.vars
            if not os.environ.get(var)
            and not local_values.get(var)
        ]

        if missing:
            return RequirementStatus(
                satisfied=False,
                detail=f"unset: {missing}",
            )

        return RequirementStatus(
            satisfied=True,
            detail="all present",
        )


@dataclass(slots=True)
class CommandRequirement(Requirement):
    """A probe command that must run and exit as expected.

    Covers external dependencies the harness can't introspect, e.g.
    a local Azure Functions host being up.
    """

    axis = CONFIG_AXIS

    argv: tuple[str, ...]

    expect_exit: int = 0

    timeout: float = 10.0

    def describe(self) -> str:
        return f"command {list(self.argv)}"

    def check(
        self,
        scenario_dir: Path,
    ) -> RequirementStatus:

        try:
            completed = subprocess.run(
                list(self.argv),
                cwd=scenario_dir,
                capture_output=True,
                timeout=self.timeout,
            )

        except FileNotFoundError:
            return RequirementStatus(
                satisfied=False,
                detail=f"{self.argv[0]} not found",
            )

        except subprocess.TimeoutExpired:
            return RequirementStatus(
                satisfied=False,
                detail="probe timed out",
            )

        if completed.returncode == self.expect_exit:
            return RequirementStatus(
                satisfied=True,
                detail=f"exit {completed.returncode}",
            )

        return RequirementStatus(
            satisfied=False,
            detail=(
                f"exit {completed.returncode} "
                f"(expected {self.expect_exit})"
            ),
        )


# ---------------------------------------------------------
# Custom — developer-supplied check, no subclass needed
# ---------------------------------------------------------

@dataclass(slots=True)
class CustomRequirement(Requirement):
    """Wraps a plain function so any condition is a requirement."""

    check_fn: CheckFn

    description: str

    axis: str = CONFIG_AXIS

    cache_key: str | None = None

    def describe(self) -> str:
        return self.description

    def suite_cache_key(self) -> str | None:
        return self.cache_key

    def check(
        self,
        scenario_dir: Path,
    ) -> RequirementStatus:

        try:
            raw = invoke_check(
                self.check_fn,
                scenario_dir,
            )

        except Exception as exc:  # noqa: BLE001 - report, never crash planning
            return RequirementStatus(
                satisfied=False,
                detail=f"check raised {type(exc).__name__}: {exc}",
            )

        return normalise_check_result(raw)
