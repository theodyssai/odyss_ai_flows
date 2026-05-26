from __future__ import annotations

from pathlib import Path

from odyss_ai_flows.core.files.api import (
    init_file_repo,
    fget,
)

from odyss_ai_flows.core.files.matcher_registry import (
    FileMatcher,
    register_matcher,
)


async def run_scenario():

    # -------------------------------------------------
    # Register custom matcher
    # -------------------------------------------------

    register_matcher(

        FileMatcher(

            kind="custom:text",

            match=lambda p: (
                p.suffix == ".txt"
            ),

            extract_name=lambda p: (
                p.stem
            ),
        )
    )

    # -------------------------------------------------
    # Init repository
    # -------------------------------------------------

    init_file_repo(
        flow_path=Path("flow"),
    )

    # -------------------------------------------------
    # Validate custom typed file
    # -------------------------------------------------

    notes = fget(
        "custom:text",
        name="notes",
    )

    assert notes is not None

    assert (
        notes.kind
        == "custom:text"
    )

    assert (
        notes.name
        == "notes"
    )

    assert (
        notes.rebased_path
        == Path("flow/notes.txt")
    )

    # -------------------------------------------------
    # Validate unknown classification removed
    # -------------------------------------------------

    unknown = fget(
        "unknown"
    )

    unknown_paths = {
        entry.rebased_path
        for entry in unknown
    }

    assert (
        Path("flow/notes.txt")
        not in unknown_paths
    )