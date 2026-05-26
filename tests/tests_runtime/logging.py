# tests/tests_runtime/logging.py

from __future__ import annotations

from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------
# Constants
# ---------------------------------------------------------

TEST_OUTPUTS_ROOT = (
    Path(__file__)
    .resolve()
    .parent
    .parent
    / "test_outputs"
)


# ---------------------------------------------------------
# Suite directories
# ---------------------------------------------------------

_current_suite_dir: Path | None = None


# ---------------------------------------------------------
# Suite lifecycle
# ---------------------------------------------------------

def create_suite_output_dir() -> Path:

    global _current_suite_dir

    timestamp = datetime.now().strftime(
        "%Y-%m-%d_%H-%M-%S"
    )

    suite_dir = (
        TEST_OUTPUTS_ROOT
        / timestamp
    )

    suite_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    _current_suite_dir = suite_dir

    return suite_dir


def get_current_suite_dir() -> Path:

    if _current_suite_dir is None:

        raise RuntimeError(
            "Suite output directory "
            "has not been initialized"
        )

    return _current_suite_dir


# ---------------------------------------------------------
# Scenario directories
# ---------------------------------------------------------

def create_scenario_output_dir(
    scenario_id: str,
) -> Path:

    suite_dir = get_current_suite_dir()

    scenario_dir = (
        suite_dir
        / Path(scenario_id)
    )

    scenario_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    return scenario_dir


# ---------------------------------------------------------
# Standardized artifact paths
# ---------------------------------------------------------

def get_scenario_log_path(
    scenario_id: str,
) -> Path:

    return (
        create_scenario_output_dir(
            scenario_id
        )
        / "scenario.log"
    )


def get_scenario_result_path(
    scenario_id: str,
) -> Path:

    return (
        create_scenario_output_dir(
            scenario_id
        )
        / "result.json"
    )


def get_suite_summary_path() -> Path:

    return (
        get_current_suite_dir()
        / "summary.json"
    )


def get_suite_log_path() -> Path:

    return (
        get_current_suite_dir()
        / "suite.log"
    )


# ---------------------------------------------------------
# Aggregation
# ---------------------------------------------------------

def aggregate_suite_logs() -> Path:

    suite_dir = get_current_suite_dir()

    suite_log_path = get_suite_log_path()

    with open(
        suite_log_path,
        "w",
        encoding="utf-8",
    ) as suite_file:

        for log_file in sorted(
            suite_dir.rglob(
                "scenario.log"
            )
        ):

            suite_file.write(
                "=" * 80
            )

            suite_file.write("\n")

            suite_file.write(
                f"SCENARIO: "
                f"{log_file.parent.relative_to(suite_dir).as_posix()}\n"
            )

            suite_file.write(
                "=" * 80
            )

            suite_file.write("\n\n")

            suite_file.write(
                log_file.read_text(
                    encoding="utf-8"
                )
            )

            suite_file.write("\n\n")

    return suite_log_path