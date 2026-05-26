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
    )

    # -------------------------------------------------
    # Build config tree
    # -------------------------------------------------

    root = await build_config_tree()

    # =================================================
    # TREE STRUCTURE
    # =================================================

    domain = root.get_child_by_path(
        "domain"
    )

    flow = root.get_child_by_path(
        "domain/flow"
    )

    nested = root.get_child_by_path(
        "domain/flow/nested"
    )

    hello = root.get_child_by_path(
        "domain/flow/hello"
    )

    assert domain is not None
    assert flow is not None
    assert nested is not None
    assert hello is not None

    # =================================================
    # GLOBAL CONFIG
    # =================================================

    assert root.config["global_scalar"] == "global"

    assert root.config["settings"] == {
        "global_only": 1,
        "shared": "global",
    }

    # =================================================
    # DOMAIN SCOPE
    # =================================================

    assert domain.config == {

        "settings": {
            "domain_only": 2,
            "shared": "domain",
        },

        "domain_scalar": "domain",
    }

    # =================================================
    # FLOW SCOPE
    # =================================================

    assert flow.config == {

        "settings": {
            "flow_only": 3,
            "shared": "flow",
        },

        "flow_scalar": "flow",
    }

    # =================================================
    # NESTED SCOPE
    # =================================================

    assert nested.config == {

        "settings": {
            "nested_only": 4,
        },

        "nested_scalar": "nested",
    }

    # =================================================
    # NODE SCOPE
    # =================================================

    assert hello.config == {

        "settings": {
            "node_only": 5,
        },

        "flow_scalar": "node_override",
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

        "global_only": 1,
        "domain_only": 2,
        "flow_only": 3,
        "node_only": 5,

        "shared": "flow",
    }

    # -------------------------------------------------
    # Scalar override
    # -------------------------------------------------

    scalar = await manager.get(

        "flow_scalar",

        node_scope=(
            "domain/flow/hello"
        ),
    )

    assert scalar == "node_override"

    # -------------------------------------------------
    # Ancestor visibility
    # -------------------------------------------------

    domain_scalar = await manager.get(

        "domain_scalar",

        node_scope=(
            "domain/flow/hello"
        ),
    )

    assert domain_scalar == "domain"

    # -------------------------------------------------
    # Nested scope isolation
    # -------------------------------------------------

    nested_only = await manager.get(

        "nested_scalar",

        node_scope=(
            "domain/flow/hello"
        ),

        default=None,
    )

    assert nested_only is None

    # -------------------------------------------------
    # Explicit scope
    # -------------------------------------------------

    explicit = await manager.get(

        "flow_scalar",

        node_scope="domain/flow",
    )

    assert explicit == "flow"

    # -------------------------------------------------
    # Default fallback
    # -------------------------------------------------

    missing = await manager.get(

        "missing.value",

        node_scope=(
            "domain/flow/hello"
        ),

        default="fallback",
    )

    assert missing == "fallback"