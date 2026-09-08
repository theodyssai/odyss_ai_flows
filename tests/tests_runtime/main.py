from __future__ import annotations

import sys

from tests.tests_runtime.discovery import (
    discover_scenarios,
)

from tests.tests_runtime.mode import (
    resolve_requested_mode,
)

from tests.tests_runtime.reporting import (
    write_suite_summary,
)

from tests.tests_runtime.runner import (
    run_test_suite,
)


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def _print_scenarios_list():

    scenarios = discover_scenarios()

    for scenario in scenarios:

        print(
            scenario.id
        )


# ---------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------

def main() -> int:

    args = sys.argv[1:]

    # -----------------------------------------------------
    # List mode
    # -----------------------------------------------------

    if "--list" in args:

        _print_scenarios_list()

        return 0

    # -----------------------------------------------------
    # Test mode (static-only vs live model execution)
    # -----------------------------------------------------

    try:
        mode = resolve_requested_mode(
            static=(
                "--static" in args
                or "--no-llm" in args
            ),
            live="--live" in args,
        )

    except ValueError as exc:

        print(f"error: {exc}")

        return 2

    # -----------------------------------------------------
    # Optional subtree filter
    # -----------------------------------------------------

    filter_prefix = None

    positional = [
        a
        for a in args
        if not a.startswith("-")
    ]

    if positional:

        filter_prefix = positional[0]

    # -----------------------------------------------------
    # Run suite
    # -----------------------------------------------------

    suite = run_test_suite(
        filter_prefix=filter_prefix,
        mode=mode,
    )

    write_suite_summary(
        suite
    )

    return 0 if suite.success else 1


# ---------------------------------------------------------
# CLI
# ---------------------------------------------------------

if __name__ == "__main__":

    raise SystemExit(
        main()
    )