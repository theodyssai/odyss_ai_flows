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

from odyss_ai_flows.core.config.exceptions import (
    ConfigReferenceCycleError,
)


async def run_scenario():

    init_file_repo(
        flow_path=Path(
            "area/flow"
        ),
    )

    root = await build_config_tree()

    manager = ConfigManager(root)

    # -------------------------------------------------
    # Mutual cycle: ref_a -> ref_b -> ref_a
    # -------------------------------------------------

    try:
        await manager.get("ref_a")

    except ConfigReferenceCycleError as exc:

        assert exc.chain[-1] == exc.chain[-3]
        assert "ref_a" in exc.chain

    else:
        raise AssertionError(
            "Expected ConfigReferenceCycleError for ref_a -> ref_b -> ref_a"
        )

    # -------------------------------------------------
    # Self cycle: self_ref -> self_ref
    # -------------------------------------------------

    try:
        await manager.get("self_ref")

    except ConfigReferenceCycleError as exc:

        assert exc.chain == ["self_ref", "self_ref"]

    else:
        raise AssertionError(
            "Expected ConfigReferenceCycleError for self_ref -> self_ref"
        )
