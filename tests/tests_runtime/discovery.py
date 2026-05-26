from __future__ import annotations

from pathlib import Path

from tests.tests_runtime.models import (
    ScenarioDefinition,
)


# ---------------------------------------------------------
# Constants
# ---------------------------------------------------------

SCENARIOS_ROOT = (
    Path(__file__)
    .resolve()
    .parent
    .parent
    / "scenarios"
)

SCENARIO_ENTRY_FILE = "scenario.py"


# ---------------------------------------------------------
# Public API
# ---------------------------------------------------------

def discover_scenarios(
    *,
    filter_prefix: str | None = None,
) -> list[ScenarioDefinition]:

    if not SCENARIOS_ROOT.exists():

        raise RuntimeError(
            f"Scenarios directory does not exist: "
            f"{SCENARIOS_ROOT}"
        )

    scenarios: list[ScenarioDefinition] = []

    for scenario_file in sorted(
        SCENARIOS_ROOT.rglob(
            SCENARIO_ENTRY_FILE
        )
    ):

        scenario_dir = (
            scenario_file.parent
        )

        relative_path = (
            scenario_dir.relative_to(
                SCENARIOS_ROOT
            )
        )

        scenario_id = (
            relative_path.as_posix()
        )

        if (
            filter_prefix
            and not scenario_id.startswith(
                filter_prefix
            )
        ):
            continue

        parts = relative_path.parts

        group = (
            parts[0]
            if len(parts) >= 2
            else None
        )

        scenarios.append(
            ScenarioDefinition(

                id=scenario_id,

                name=parts[-1],

                group=group,

                relative_path=relative_path,

                path=scenario_dir,

                scenario_file=scenario_file,
            )
        )

    scenarios.sort(
        key=lambda s: s.id
    )

    return scenarios