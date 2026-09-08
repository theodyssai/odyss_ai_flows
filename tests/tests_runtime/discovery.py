from __future__ import annotations

import importlib.util
import re

from pathlib import Path

from tests.tests_runtime.models import (
    ScenarioDefinition,
)

from tests.tests_runtime.requirements import (
    Requirement,
    coerce_requirements,
    default_llm_requirements,
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

SCENARIO_REQUIREMENTS_FILE = "requirements.py"

SCENARIO_REQUIREMENTS_EXPORT = "REQUIREMENTS"

_REQUIRES_LLM_OVERRIDE = re.compile(
    r"^\s*REQUIRES_LLM\s*=\s*(True|False)\b",
    re.MULTILINE,
)

_EXECUTES_FLOW = re.compile(
    r"\b(run_flow|ScenarioRuntimeDefinition)\b",
)


def _scenario_requires_llm(
    scenario_file: Path,
) -> bool:

    try:
        source = scenario_file.read_text(
            encoding="utf-8"
        )

    except OSError:
        source = ""

    # Explicit override wins.
    override = _REQUIRES_LLM_OVERRIDE.search(
        source
    )

    if override:
        return override.group(1) == "True"

    # Auto-detect.
    has_jinja_node = any(
        scenario_file.parent.rglob("*.jinja2")
    )

    executes_flow = bool(
        _EXECUTES_FLOW.search(source)
    )

    return has_jinja_node and executes_flow


def _load_requirements_export(
    sidecar: Path,
    scenario_id: str,
):
    module_name = (
        "scenario_requirements_"
        + re.sub(r"\W+", "_", scenario_id)
    )

    spec = importlib.util.spec_from_file_location(
        module_name,
        str(sidecar),
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"Could not load requirements module: {sidecar}"
        )

    module = importlib.util.module_from_spec(spec)

    spec.loader.exec_module(module)

    return getattr(
        module,
        SCENARIO_REQUIREMENTS_EXPORT,
        None,
    )


def _scenario_requirements(
    scenario_dir: Path,
    scenario_file: Path,
    scenario_id: str,
) -> list[Requirement]:

    sidecar = (
        scenario_dir
        / SCENARIO_REQUIREMENTS_FILE
    )

    if sidecar.is_file():
        exported = _load_requirements_export(
            sidecar,
            scenario_id,
        )

        return coerce_requirements(exported)

    if _scenario_requires_llm(scenario_file):
        return default_llm_requirements()

    return []


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

                requirements=_scenario_requirements(
                    scenario_dir,
                    scenario_file,
                    scenario_id,
                ),
            )
        )

    scenarios.sort(
        key=lambda s: s.id
    )

    return scenarios