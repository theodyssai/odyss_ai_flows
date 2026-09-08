from __future__ import annotations

import inspect

from importlib.metadata import entry_points
from pathlib import Path

from tests.tests_runtime.requirements.base import (
    CheckFn,
    CheckResult,
    RequirementStatus,
)


def invoke_check(
    check_fn: CheckFn,
    scenario_dir: Path,
) -> CheckResult:

    try:
        takes_arg = bool(
            inspect.signature(check_fn).parameters
        )

    except (TypeError, ValueError):
        takes_arg = True

    if takes_arg:
        return check_fn(scenario_dir)

    return check_fn()


def normalise_check_result(
    raw: CheckResult,
) -> RequirementStatus:

    if isinstance(raw, RequirementStatus):
        return raw

    if (
        isinstance(raw, tuple)
        and len(raw) == 2
        and isinstance(raw[0], bool)
    ):
        return RequirementStatus(
            satisfied=raw[0],
            detail=str(raw[1]),
        )

    return RequirementStatus(
        satisfied=bool(raw),
        detail="ok" if raw else "check returned falsey",
    )


def entry_points_for(group: str) -> list:
    try:
        return list(
            entry_points(group=group)
        )

    except TypeError:
        # importlib.metadata < 3.10 API
        return list(
            entry_points().get(group, [])
        )


def read_env_local(
    path: Path,
) -> dict[str, str]:

    if not path.is_file():
        return {}

    try:
        raw_text = path.read_text(
            encoding="utf-8"
        )

    except OSError:
        return {}

    values: dict[str, str] = {}

    for raw in raw_text.splitlines():

        line = raw.strip()

        if not line or line.startswith("#"):
            continue

        key, sep, value = line.partition("=")

        if sep:
            values[key.strip()] = value.strip()

    return values
