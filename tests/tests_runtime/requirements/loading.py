# tests/tests_runtime/requirements/loading.py

from __future__ import annotations

from typing import Any

from tests.tests_runtime.requirements.base import Requirement
from tests.tests_runtime.requirements.builder import azure


def coerce_requirements(value: Any) -> list[Requirement]:
    """Normalise a scenario's ``REQUIREMENTS`` export into a flat list.

    Accepts a Requirement, a list/tuple of them, a zero-arg callable
    returning either, or ``None``. Nested lists (e.g. ``[*azure(), x]``
    written as ``[azure(), x]``) are flattened one level for convenience.
    """

    if value is None:
        return []

    if callable(value) and not isinstance(value, Requirement):
        value = value()

    if isinstance(value, Requirement):
        return [value]

    if isinstance(value, (list, tuple)):
        flat: list[Requirement] = []

        for item in value:

            if isinstance(item, Requirement):
                flat.append(item)

            elif isinstance(item, (list, tuple)):
                flat.extend(
                    coerce_requirements(item)
                )

            else:
                raise TypeError(
                    f"REQUIREMENTS entries must be Requirement "
                    f"instances, got {type(item).__name__}"
                )

        return flat

    raise TypeError(
        f"REQUIREMENTS must be a Requirement or a list of them, "
        f"got {type(value).__name__}"
    )


def default_llm_requirements() -> list[Requirement]:
    """Auto-classification fallback for jinja scenarios (see discovery)."""

    return azure()
