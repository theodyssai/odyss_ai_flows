from __future__ import annotations

from pathlib import Path

from odyss_ai_flows.core.files.api import (
    init_file_repo,
    fget,
)


async def run_scenario():

    # -------------------------------------------------
    # Init repository
    # -------------------------------------------------

    init_file_repo(
        flow_path=Path(
            "area/flow"
        ),
    )

    # -------------------------------------------------
    # Collect folder configs
    # -------------------------------------------------

    configs = fget(
        "config:folder"
    )

    # -------------------------------------------------
    # Validate scopes
    # -------------------------------------------------

    scopes = {
        entry.rebased_path
        for entry in configs
    }

    assert scopes == {
        Path("area"),
        Path("area/flow"),
        Path("area/flow/nested"),
    }

    # -------------------------------------------------
    # Validate sources
    # -------------------------------------------------

    by_scope = {
        entry.rebased_path: entry
        for entry in configs
    }

    assert (
        by_scope[
            Path("area")
        ].source
        == "linear"
    )

    assert (
        by_scope[
            Path("area/flow")
        ].source
        == "base"
    )

    assert (
        by_scope[
            Path(
                "area/flow/nested"
            )
        ].source
        == "base"
    )
    
    # -------------------------------------------------
    # Validate sibling scope is ignored
    # -------------------------------------------------

    assert (
        Path("area/side")
        not in scopes
    )