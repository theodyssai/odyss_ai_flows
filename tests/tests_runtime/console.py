# tests/tests_runtime/console.py

from __future__ import annotations

from rich.console import Console
from rich.table import Table

from tests.tests_runtime.mode import (
    SuitePlan,
    TestMode,
)

from tests.tests_runtime.models import (
    ScenarioDefinition,
    ScenarioResult,
    SuiteResult,
)


console = Console()


# ---------------------------------------------------------
# Mode communication
# ---------------------------------------------------------

_MODE_LABELS = {
    TestMode.AUTO: "AUTO",
    TestMode.STATIC: "STATIC-ONLY",
    TestMode.LIVE: "LIVE",
}


def print_mode_banner(
    plan: SuitePlan,
) -> None:

    label = _MODE_LABELS[plan.requested]

    console.print(
        f"[bold]Test mode:[/bold] "
        f"[bold magenta]{label}[/bold magenta]"
    )

    for describe, installed in sorted(
        plan.referenced_plugins.items()
    ):
        state = (
            "[green]installed[/green]"
            if installed
            else "[red]not installed[/red]"
        )

        console.print(
            f"Required {describe}: {state}"
        )

    if plan.req_total:

        resolved_colour = (
            "green"
            if plan.req_resolvable
            == plan.req_total
            else "yellow"
        )

        console.print(
            f"Requirements: "
            f"[{resolved_colour}]"
            f"{plan.req_resolvable}/"
            f"{plan.req_total}[/{resolved_colour}] "
            f"scenario(s) fully satisfied "
            f"[dim](plugin + config)[/dim]"
        )

        static_total = (
            len(plan.plans)
            - plan.req_total
        )

        console.print(
            f"Requirement scenarios: {plan.req_total} "
            f"of {len(plan.plans)} — "
            f"[green]{plan.req_run} run[/green], "
            f"[yellow]{plan.req_skipped} "
            f"skipped[/yellow] "
            f"[dim]({static_total} static, always run)[/dim]"
        )

    console.print()


def print_warnings(
    warnings: list[str],
) -> None:

    for warning in warnings:
        console.print(
            f"[bold yellow]WARNING:[/bold yellow] "
            f"{warning}"
        )

    if warnings:
        console.print()


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


def print_scenario_skip(
    scenario: ScenarioDefinition,
    reason: str | None,
) -> None:

    console.print(
        f"[yellow]SKIP[/yellow] "
        f"{scenario.id} "
        f"[dim]({reason})[/dim]"
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
        "Skipped",
        str(suite.skipped),
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

    # Make it unmistakable which tests did not actually run.

    skipped = [
        r
        for r in suite.scenario_results
        if r.skipped
    ]

    if skipped:

        console.print()

        console.print(
            "[yellow]Skipped (not executed):"
            "[/yellow]"
        )

        for r in skipped:
            console.print(
                f"  [yellow]-[/yellow] "
                f"{r.scenario.id} "
                f"[dim]({r.skip_reason})[/dim]"
            )