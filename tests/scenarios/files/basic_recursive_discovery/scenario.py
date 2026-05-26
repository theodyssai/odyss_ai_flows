from __future__ import annotations

from pathlib import Path

from odyss_ai_flows.core.files.api import (
    init_file_repo,
    fget,
)

from odyss_ai_flows.core.files.repository import (
    FileRepository,
)


async def run_scenario():

    # ---------------------------------------------------------
    # Init repository
    # ---------------------------------------------------------

    init_file_repo(
        flow_path=Path("flow"),
    )

    # ---------------------------------------------------------
    # Validate python nodes
    # ---------------------------------------------------------

    python_nodes = fget("node:python")

    python_names = {
        entry.name
        for entry in python_nodes
    }

    assert python_names == {
        "hello",
        "world",
    }

    # ---------------------------------------------------------
    # Validate jinja nodes
    # ---------------------------------------------------------

    jinja_nodes = fget(
        "node:jinja"
    )

    assert len(jinja_nodes) == 1

    assert (
        jinja_nodes[0].name
        == "world"
    )

    # ---------------------------------------------------------
    # Validate model files
    # ---------------------------------------------------------

    model = fget(
        "node:model",
        name="hello",
    )

    assert model is not None

    assert (
        model.rebased_path
        == Path(
            "flow/hello.model.py"
        )
    )

    # ---------------------------------------------------------
    # Validate node config
    # ---------------------------------------------------------

    node_config = fget(
        "config:node",
        name="hello",
    )

    assert node_config is not None

    # ---------------------------------------------------------
    # Validate outputs
    # ---------------------------------------------------------

    outputs = fget(
        "flow:outputs"
    )

    assert len(outputs) == 1

    # ---------------------------------------------------------
    # Validate rebased lookup
    # ---------------------------------------------------------

    world = fget(
        "node:python",
        rebased_path=Path(
            "flow/nested/world.py"
        )
    )

    assert world is not None

    assert world.name == "world"

    # ---------------------------------------------------------
    # Validate recursive config discovery
    # ---------------------------------------------------------

    folder_configs = fget(
        "config:folder"
    )

    rebased = {
        entry.rebased_path
        for entry in folder_configs
    }

    assert rebased == {
        Path("flow"),
        Path("flow/nested"),
    }

    # ---------------------------------------------------------
    # Validate unknown file preservation
    # ---------------------------------------------------------

    unknown_files = fget(
        "unknown"
    )

    unknown_paths = {
        entry.rebased_path
        for entry in unknown_files
    }

    assert (
        Path("flow/notes.txt")
        in unknown_paths
    )

    assert (
        Path(
            "flow/nested/ignored.tmp"
        )
        in unknown_paths
    )