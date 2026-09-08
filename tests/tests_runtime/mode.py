# tests/tests_runtime/mode.py

from __future__ import annotations

import os

from dataclasses import dataclass, field
from enum import Enum

from tests.tests_runtime.models import (
    ScenarioDefinition,
)

from tests.tests_runtime.requirements import (
    PLUGIN_AXIS,
    Requirement,
    RequirementStatus,
)


# ---------------------------------------------------------
# Constants
# ---------------------------------------------------------

MODE_ENV_VAR = "ODYSS_TEST_MODE"


# ---------------------------------------------------------
# Mode
# ---------------------------------------------------------

class TestMode(str, Enum):
    AUTO = "auto"
    STATIC = "static"
    LIVE = "live"


# ---------------------------------------------------------
# Plans
# ---------------------------------------------------------

@dataclass(slots=True)
class ScenarioPlan:
    scenario: ScenarioDefinition

    run: bool

    skip_reason: str | None = None

    statuses: list[
        tuple[Requirement, RequirementStatus]
    ] = field(default_factory=list)


@dataclass(slots=True)
class SuitePlan:
    requested: TestMode

    plans: list[ScenarioPlan]

    warnings: list[str] = field(
        default_factory=list
    )

    referenced_plugins: dict[str, bool] = field(
        default_factory=dict
    )

    req_total: int = 0

    req_run: int = 0

    req_skipped: int = 0

    req_resolvable: int = 0


# ---------------------------------------------------------
# Mode resolution
# ---------------------------------------------------------

def resolve_requested_mode(
    *,
    static: bool,
    live: bool,
) -> TestMode:
    """CLI flags take precedence, then ``ODYSS_TEST_MODE``."""

    if static and live:
        raise ValueError(
            "Cannot combine --static and --live"
        )

    if static:
        return TestMode.STATIC

    if live:
        return TestMode.LIVE

    env_value = (
        os.environ
        .get(MODE_ENV_VAR, "")
        .strip()
        .lower()
    )

    if env_value:
        try:
            return TestMode(env_value)

        except ValueError:
            raise ValueError(
                f"Invalid {MODE_ENV_VAR}="
                f"{env_value!r} "
                f"(expected auto|static|live)"
            )

    return TestMode.AUTO


# ---------------------------------------------------------
# Planning
# ---------------------------------------------------------

def _unmet_summary(
    pairs: list[
        tuple[Requirement, RequirementStatus]
    ],
) -> str:

    return ", ".join(
        f"{req.describe()} ({status.detail})"
        for req, status in pairs
    )


def build_suite_plan(
    scenarios: list[ScenarioDefinition],
    requested: TestMode,
) -> SuitePlan:

    plan = SuitePlan(
        requested=requested,
        plans=[],
    )

    plugin_missing_seen = False

    for scenario in scenarios:

        if not scenario.requirements:
            plan.plans.append(
                ScenarioPlan(
                    scenario=scenario,
                    run=True,
                )
            )
            continue

        plan.req_total += 1

        statuses = [
            (req, req.check(scenario.path))
            for req in scenario.requirements
        ]

        plugin_unmet = [
            (req, st)
            for req, st in statuses
            if req.axis == PLUGIN_AXIS
            and not st.satisfied
        ]

        config_unmet = [
            (req, st)
            for req, st in statuses
            if req.axis != PLUGIN_AXIS
            and not st.satisfied
        ]

        for req, st in statuses:
            if req.axis == PLUGIN_AXIS:
                plan.referenced_plugins[
                    req.describe()
                ] = st.satisfied

        if not plugin_unmet and not config_unmet:
            plan.req_resolvable += 1

        # ---------------------------------------------
        # Missing plugin: hard prerequisite, skip in ALL
        # modes (the scenario cannot even import).
        # ---------------------------------------------

        if plugin_unmet:
            plugin_missing_seen = True

            plan.plans.append(
                ScenarioPlan(
                    scenario=scenario,
                    run=False,
                    skip_reason=(
                        "missing "
                        + _unmet_summary(plugin_unmet)
                    ),
                    statuses=statuses,
                )
            )
            plan.req_skipped += 1
            continue

        # ---------------------------------------------
        # Static: never run requirement-bearing scenarios.
        # ---------------------------------------------

        if requested == TestMode.STATIC:
            plan.plans.append(
                ScenarioPlan(
                    scenario=scenario,
                    run=False,
                    skip_reason="static-only mode",
                    statuses=statuses,
                )
            )
            plan.req_skipped += 1
            continue

        # ---------------------------------------------
        # Live: always run; warn if config is missing so
        # it fails honestly instead of silently passing.
        # ---------------------------------------------

        if requested == TestMode.LIVE:
            plan.plans.append(
                ScenarioPlan(
                    scenario=scenario,
                    run=True,
                    statuses=statuses,
                )
            )
            plan.req_run += 1

            if config_unmet:
                plan.warnings.append(
                    f"LIVE mode: '{scenario.id}' "
                    f"is missing config "
                    f"{_unmet_summary(config_unmet)} "
                    f"and will likely FAIL "
                    f"(not skipped)."
                )

            continue

        # ---------------------------------------------
        # Auto: run only when config is satisfied.
        # ---------------------------------------------

        if config_unmet:
            plan.plans.append(
                ScenarioPlan(
                    scenario=scenario,
                    run=False,
                    skip_reason=(
                        "missing config: "
                        + _unmet_summary(config_unmet)
                    ),
                    statuses=statuses,
                )
            )
            plan.req_skipped += 1

        else:
            plan.plans.append(
                ScenarioPlan(
                    scenario=scenario,
                    run=True,
                    statuses=statuses,
                )
            )
            plan.req_run += 1

    # -----------------------------------------------------
    # Suite-level warnings
    # -----------------------------------------------------

    if plugin_missing_seen:
        plan.warnings.append(
            "One or more required plugins are not "
            "installed; affected scenario(s) SKIPPED in "
            "all modes (cannot import the plugin). Install "
            "the plugin, e.g. `pip install -e "
            "plugins/odyss_ai_flows_azure`."
        )

    elif (
        requested == TestMode.AUTO
        and plan.req_skipped
    ):
        plan.warnings.append(
            f"AUTO mode: required config not found for "
            f"{plan.req_skipped} scenario(s) (no exported "
            f"env vars / no .env.local / probe failed); "
            f"SKIPPED. Provide the config or run --live to "
            f"force them."
        )

    return plan
