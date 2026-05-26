from __future__ import annotations

from pathlib import Path

from odyss_ai_flows.core.files.api import (
    init_file_repo,
    fget,
)


async def run_scenario():

    # =================================================
    # SINGLE VARIANT
    # =================================================

    init_file_repo(
        flow_path=Path("flow"),
        variant_paths=[
            Path("variants/v1"),
        ],
    )

    # -------------------------------------------------
    # Base file still exists
    # -------------------------------------------------

    hello = fget(
        "node:python",
        name="hello",
    )

    assert hello is not None

    assert hello.source == "base"

    # -------------------------------------------------
    # Variant override works
    # -------------------------------------------------

    world = fget(
        "node:python",
        name="world",
    )

    assert world is not None

    assert world.source == "variant:0"

    assert (
        world.real_path
        == Path(
            "variants/v1/world.py"
        )
    )

    # -------------------------------------------------
    # Variant can add new files
    # -------------------------------------------------

    new_node = fget(
        "node:python",
        name="new_node",
    )

    assert new_node is not None

    assert new_node.source == "variant:0"

    # -------------------------------------------------
    # Rebased paths preserved
    # -------------------------------------------------

    assert (
        world.rebased_path
        == Path("flow/world.py")
    )

    assert (
        new_node.rebased_path
        == Path("flow/new_node.py")
    )

    # -------------------------------------------------
    # Nested config preserved
    # -------------------------------------------------

    configs = fget(
        "config:folder"
    )

    nested_configs = [
        entry
        for entry in configs
        if entry.rebased_path
        == Path("flow/nested")
    ]

    sources = {
    entry.source
    for entry in nested_configs
    }

    assert sources == {
        "base",
        "variant:0",
    }

    # =================================================
    # MULTI VARIANT
    # =================================================

    init_file_repo(
        flow_path=Path("flow"),
        variant_paths=[
            Path("variants/v1"),
            Path("variants/v2"),
        ],
    )

    # -------------------------------------------------
    # Later variant overrides earlier variant
    # -------------------------------------------------

    world = fget(
        "node:python",
        name="world",
    )

    assert world is not None

    assert world.source == "variant:1"

    assert (
        world.real_path
        == Path(
            "variants/v2/world.py"
        )
    )

    # -------------------------------------------------
    # Nested override works
    # -------------------------------------------------

    deep = fget(
        "node:python",
        name="deep",
    )

    assert deep is not None

    assert deep.source == "variant:1"

    assert (
        deep.real_path
        == Path(
            "variants/v2/nested/deep.py"
        )
    )

    # -------------------------------------------------
    # Additive files still preserved
    # -------------------------------------------------

    new_node = fget(
        "node:python",
        name="new_node",
    )

    assert new_node is not None

    assert new_node.source == "variant:0"

    # -------------------------------------------------
    # Outputs overridden
    # -------------------------------------------------

    outputs = fget(
        "flow:outputs"
    )

    assert len(outputs) == 1

    assert (
        outputs[0].source
        == "variant:1"
    )
    
    assert (
    outputs[0].real_path
    == Path(
        "variants/v2/outputs.json"
    )
)