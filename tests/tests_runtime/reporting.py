# tests/tests_runtime/reporting.py

from __future__ import annotations

import json

from tests.tests_runtime.logging import (
    get_suite_summary_path,
)

from tests.tests_runtime.models import (
    SuiteResult,
)


# ---------------------------------------------------------
# Public API
# ---------------------------------------------------------

def write_suite_summary(
    suite: SuiteResult,
) -> None:

    payload = {
        "started_at": suite.started_at,
        "finished_at": suite.finished_at,

        "duration_seconds": (
            suite.duration_seconds
        ),

        "success": suite.success,

        "total": suite.total,
        "passed": suite.passed,
        "failed": suite.failed,
        "skipped": suite.skipped,

        "scenarios": [
            {
                "id": r.scenario.id,
                "name": r.scenario.name,

                "success": r.success,

                "skipped": r.skipped,

                "skip_reason": r.skip_reason,

                "requirements": [
                    req.describe()
                    for req in r.scenario.requirements
                ],

                "duration_seconds": (
                    r.duration_seconds
                ),

                "error": (
                    str(r.error)
                    if r.error
                    else None
                ),

                "logs_path": (
                    str(r.logs_path)
                    if r.logs_path
                    else None
                ),
            }

            for r in suite.scenario_results
        ],
    }

    summary_path = (
        get_suite_summary_path()
    )

    summary_path.write_text(
        json.dumps(
            payload,
            indent=4,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )