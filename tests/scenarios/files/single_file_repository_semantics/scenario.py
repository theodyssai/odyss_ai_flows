from __future__ import annotations

from pathlib import Path

from odyss_ai_flows.core.files.api import (
    init_file_repo,
    fget,
)


async def run_scenario():

    # -------------------------------------------------
    # Init single-file repository
    # -------------------------------------------------

    init_file_repo(
        flow_path=Path(
            "domain/flow/hello.py"
        ),
    )

    # -------------------------------------------------
    # Validate python node
    # -------------------------------------------------

    python_nodes = fget(
        "node:python"
    )

    assert len(python_nodes) == 1

    hello = python_nodes[0]

    assert hello.name == "hello"

    assert (
        hello.rebased_path
        == Path(
            "domain/flow/hello.py"
        )
    )

    # -------------------------------------------------
    # Validate model discovery
    # -------------------------------------------------

    model = fget(
        "node:model",
        name="hello",
    )

    assert model is not None

    assert (
        model.rebased_path
        == Path(
            "domain/flow/hello.model.py"
        )
    )

    # -------------------------------------------------
    # Validate node config discovery
    # -------------------------------------------------

    node_config = fget(
        "config:node",
        name="hello",
    )

    assert node_config is not None

    # -------------------------------------------------
    # Validate folder config scopes
    # -------------------------------------------------

    folder_configs = fget(
        "config:folder"
    )

    scopes = {
        entry.rebased_path
        for entry in folder_configs
    }

    assert scopes == {
        Path("domain"),
        Path("domain/flow"),
    }

    # -------------------------------------------------
    # Validate source semantics
    # -------------------------------------------------

    by_scope = {
        entry.rebased_path: entry
        for entry in folder_configs
    }

    # ancestor config discovered
    # through linear scan

    assert (
        by_scope[
            Path("domain")
        ].source
        == "linear"
    )

    # flow-local config discovered
    # directly in flow scope

    assert (
        by_scope[
            Path("domain/flow")
        ].source
        == "base"
    )

    # -------------------------------------------------
    # Validate no unrelated nodes
    # -------------------------------------------------

    assert fget(
        "node:python",
        name="world",
    ) is None