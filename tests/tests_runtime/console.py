# tests/tests_runtime/console.py

from __future__ import annotations

from rich.console import Console
from rich.table import Table

from tests.tests_runtime.models import (
    ScenarioDefinition,
    ScenarioResult,
    SuiteResult,
)


console = Console()


# ---------------------------------------------------------
# Suite lifecycle
# ---------------------------------------------------------

def print_suite_start(
    total_scenarios: int,
) -> None:

    console.rule(
        f"[bold cyan]AI Flows Test Suite[/bold cyan]"
    )

    console.print(
        f"Discovered scenarios: "
        f"[bold]{total_scenarios}[/bold]"
    )

    console.print()


# ---------------------------------------------------------
# Scenario lifecycle
# ---------------------------------------------------------

def print_scenario_start(
    scenario: ScenarioDefinition,
) -> None:

    console.print(
        f"[cyan]RUN[/cyan] "
        f"{scenario.id}"
    )


def print_scenario_result(
    result: ScenarioResult,
) -> None:

    status = (
        "[green]PASS[/green]"
        if result.success
        else "[red]FAIL[/red]"
    )

    console.print(
        f"{status} "
        f"{result.scenario.id} "
        f"[dim]"
        f"({result.duration_seconds:.2f}s)"
        f"[/dim]"
    )

    if result.error is not None:

        console.print(
            f"  [red]{result.error.type}:[/red] "
            f"{result.error.message}"
        )

        if result.error.traceback:

            console.print()

            console.print(
                "[dim]"
                f"{result.error.traceback}"
                "[/dim]"
            )


# ---------------------------------------------------------
# Final summary
# ---------------------------------------------------------

def print_suite_summary(
    suite: SuiteResult,
) -> None:

    console.print()
    console.rule(
        "[bold cyan]Suite Summary[/bold cyan]"
    )

    table = Table()

    table.add_column("Metric")
    table.add_column("Value")

    table.add_row(
        "Total",
        str(suite.total),
    )

    table.add_row(
        "Passed",
        str(suite.passed),
    )

    table.add_row(
        "Failed",
        str(suite.failed),
    )

    table.add_row(
        "Duration",
        f"{suite.duration_seconds:.2f}s",
    )

    overall = (
        "[green]SUCCESS[/green]"
        if suite.success
        else "[red]FAILURE[/red]"
    )

    table.add_row(
        "Overall",
        overall,
    )

    console.print(table)