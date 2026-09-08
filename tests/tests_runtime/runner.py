# tests/tests_runtime/runner.py

from __future__ import annotations

import time

from datetime import datetime

from tests.tests_runtime.console import (
    print_mode_banner,
    print_scenario_result,
    print_scenario_skip,
    print_scenario_start,
    print_suite_start,
    print_suite_summary,
    print_warnings,
)

from tests.tests_runtime.discovery import (
    discover_scenarios,
)

from tests.tests_runtime.logging import (
    aggregate_suite_logs,
    create_suite_output_dir,
)

from tests.tests_runtime.mode import (
    TestMode,
    build_suite_plan,
)

from tests.tests_runtime.models import (
    ScenarioResult,
    SuiteResult,
)

from tests.tests_runtime.process_runner import (
    run_scenario_in_subprocess,
)


# ---------------------------------------------------------
# Public API
# ---------------------------------------------------------

def run_test_suite(
    *,
    filter_prefix: str | None = None,
    mode: TestMode = TestMode.AUTO,
) -> SuiteResult:

    suite_started = time.perf_counter()

    started_at = datetime.now().isoformat()

    create_suite_output_dir()

    scenarios = discover_scenarios(
        filter_prefix=filter_prefix
    )

    plan = build_suite_plan(
        scenarios,
        mode,
    )

    print_suite_start(
        len(scenarios)
    )

    print_mode_banner(
        plan
    )

    print_warnings(
        plan.warnings
    )

    scenario_results = []

    # ---------------------------------------------------------
    # Sequential execution
    # ---------------------------------------------------------

    for scenario_plan in plan.plans:

        scenario = scenario_plan.scenario

        if not scenario_plan.run:

            print_scenario_skip(
                scenario,
                scenario_plan.skip_reason,
            )

            scenario_results.append(
                ScenarioResult(
                    scenario=scenario,
                    success=False,
                    duration_seconds=0.0,
                    skipped=True,
                    skip_reason=(
                        scenario_plan.skip_reason
                    ),
                )
            )

            continue

        print_scenario_start(
            scenario
        )

        result = run_scenario_in_subprocess(
            scenario
        )

        scenario_results.append(
            result
        )

        print_scenario_result(
            result
        )

    # ---------------------------------------------------------
    # Finalization
    # ---------------------------------------------------------

    aggregate_suite_logs()

    duration = (
        time.perf_counter()
        - suite_started
    )

    suite = SuiteResult(
        started_at=started_at,
        finished_at=datetime.now().isoformat(),
        duration_seconds=duration,
        scenario_results=scenario_results,
    )

    print_suite_summary(
        suite
    )

    return suite