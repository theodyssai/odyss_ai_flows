from __future__ import annotations

from pathlib import Path

from odyss_ai_flows.core.files.api import (
    init_file_repo,
)

from odyss_ai_flows.core.config.builder import (
    build_config_tree,
)

from odyss_ai_flows.core.config.manager import (
    ConfigManager,
)


async def run_scenario():

    # -------------------------------------------------
    # Init repository
    # -------------------------------------------------

    init_file_repo(

        flow_path=Path(
            "domain/flow"
        ),

        variant_paths=[

            Path(
                "variants/v1/flow"
            ),

            Path(
                "variants/v2/flow"
            ),
        ],
    )

    # -------------------------------------------------
    # Build tree
    # -------------------------------------------------

    root = await build_config_tree()

    # -------------------------------------------------
    # Resolve scopes
    # -------------------------------------------------

    flow = root.get_child_by_path(
        "domain/flow"
    )

    hello = root.get_child_by_path(
        "domain/flow/hello"
    )

    assert flow is not None
    assert hello is not None

    # =================================================
    # RAW TREE VALIDATION
    # =================================================

    assert flow.config == {

        "settings": {

            "base": True,
            "v1": True,
            "v2": True,

            "shared": "v2",
        },

        "model": "gpt4",

        "temperature": 0.5,

        "list_value": [9],
    }

    assert hello.config == {

        "node_mode": "variant2",

        "node_dict": {

            "base": True,
            "v1": True,
            "v2": True,
        }
    }

    # =================================================
    # MANAGER RESOLUTION
    # =================================================

    manager = ConfigManager(root)

    resolved = await manager.get(

        "settings",

        node_scope=(
            "domain/flow/hello"
        ),
    )

    assert resolved == {

        "base": True,
        "v1": True,
        "v2": True,

        "shared": "v2",
    }

    # -------------------------------------------------
    # Scalar precedence
    # -------------------------------------------------

    node_mode = await manager.get(

        "node_mode",

        node_scope=(
            "domain/flow/hello"
        ),
    )

    assert node_mode == "variant2"

    # -------------------------------------------------
    # List replacement
    # -------------------------------------------------

    list_value = await manager.get(

        "list_value",

        node_scope=(
            "domain/flow/hello"
        ),
    )

    assert list_value == [9]

    # -------------------------------------------------
    # Inherited untouched values
    # -------------------------------------------------

    model = await manager.get(

        "model",

        node_scope=(
            "domain/flow/hello"
        ),
    )

    assert model == "gpt4"