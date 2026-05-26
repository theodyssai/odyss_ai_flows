# tests/tests_runtime/process_runner.py

from __future__ import annotations

import json
import os
import subprocess
import sys
import time

from pathlib import Path

from tests.tests_runtime.logging import (
    get_scenario_log_path,
    get_scenario_result_path,
)

from tests.tests_runtime.models import (
    ScenarioDefinition,
    ScenarioError,
    ScenarioResult,
)


# ---------------------------------------------------------
# Constants
# ---------------------------------------------------------

SCENARIO_ENTRY_MODULE = (
    "tests.tests_runtime.scenario_entry"
)

DEFAULT_SCENARIO_TIMEOUT_SECONDS = 300


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def _build_subprocess_env() -> dict[str, str]:

    env = os.environ.copy()

    repo_root = (
        Path(__file__)
        .resolve()
        .parents[2]
    )

    existing_pythonpath = env.get(
        "PYTHONPATH",
        "",
    )

    env["PYTHONPATH"] = (
        str(repo_root)

        if not existing_pythonpath

        else (
            f"{repo_root}"
            f"{os.pathsep}"
            f"{existing_pythonpath}"
        )
    )

    return env


# ---------------------------------------------------------
# Public API
# ---------------------------------------------------------

def run_scenario_in_subprocess(
    scenario: ScenarioDefinition,
    *,
    timeout_seconds: int = DEFAULT_SCENARIO_TIMEOUT_SECONDS,
) -> ScenarioResult:

    started = time.perf_counter()

    log_path = (
        get_scenario_log_path(
            scenario.id
        )
        .resolve()
    )

    result_path = (
        get_scenario_result_path(
            scenario.id
        )
        .resolve()
    )

    scenario_file = (
        scenario.scenario_file
        .resolve()
    )

    cmd = [
        sys.executable,
        "-m",
        SCENARIO_ENTRY_MODULE,

        str(scenario_file),
        str(result_path),
        str(log_path),
    ]

    process_result = None

    timeout_hit = False

    try:

        process_result = subprocess.run(
            cmd,

            cwd=scenario.path,

            env=_build_subprocess_env(),

            timeout=timeout_seconds,

            capture_output=True,

            text=True,
        )

    except subprocess.TimeoutExpired:

        timeout_hit = True

    duration = (
        time.perf_counter()
        - started
    )

    # ---------------------------------------------------------
    # Timeout
    # ---------------------------------------------------------

    if timeout_hit:

        return ScenarioResult(
            scenario=scenario,

            success=False,

            duration_seconds=duration,

            error=ScenarioError(
                type="TimeoutError",

                message=(
                    f"Scenario exceeded timeout "
                    f"({timeout_seconds}s)"
                ),

                traceback="",
            ),

            logs_path=log_path,
        )

    # ---------------------------------------------------------
    # Missing result
    # ---------------------------------------------------------

    if not result_path.is_file():

        stderr = (
            process_result.stderr.strip()

            if process_result
            and process_result.stderr

            else "No stderr captured"
        )

        return ScenarioResult(
            scenario=scenario,

            success=False,

            duration_seconds=duration,

            error=ScenarioError(
                type="ScenarioProcessError",

                message=(
                    "Scenario process did not "
                    "produce result.json"
                ),

                traceback=stderr,
            ),

            logs_path=log_path,
        )

    # ---------------------------------------------------------
    # Load structured result
    # ---------------------------------------------------------

    try:

        payload = json.loads(
            result_path.read_text(
                encoding="utf-8"
            )
        )

    except Exception as e:

        return ScenarioResult(
            scenario=scenario,

            success=False,

            duration_seconds=duration,

            error=ScenarioError(
                type=type(e).__name__,

                message=(
                    f"Failed to parse result.json: "
                    f"{e}"
                ),

                traceback="",
            ),

            logs_path=log_path,
        )

    # ---------------------------------------------------------
    # Final model
    # ---------------------------------------------------------

    success = bool(
        payload.get(
            "success",
            False,
        )
    )

    error_payload = payload.get(
        "error"
    )

    return ScenarioResult(
        scenario=scenario,

        success=success,

        duration_seconds=duration,

        result=payload.get(
            "result"
        ),

        error=(
            ScenarioError(
                type=error_payload.get(
                    "type",
                    "UnknownError",
                ),

                message=error_payload.get(
                    "message",
                    "",
                ),

                traceback=error_payload.get(
                    "traceback",
                    "",
                ),
            )

            if error_payload
            else None
        ),

        logs_path=log_path,
    )