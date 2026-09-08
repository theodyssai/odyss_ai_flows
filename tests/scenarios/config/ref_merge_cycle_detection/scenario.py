from __future__ import annotations

from pathlib import Path

from odyss_ai_flows.core.files.api import (
    init_file_repo,
)

from odyss_ai_flows.core.config.builder import (
    build_config_tree,
)

from odyss_ai_flows.core.config.exceptions import (
    ConfigMergeCycleError,
)


async def run_scenario():

    init_file_repo(
        flow_path=Path(
            "area/flow"
        ),
    )

    try:
        await build_config_tree()

    except ConfigMergeCycleError as exc:

        # Chain must end where it started (the cycle close).
        assert exc.chain[-1] == exc.chain[-3]

        assert "cycle_a.json" in str(exc)

        return

    raise AssertionError(
        "Expected ConfigMergeCycleError for circular $REF"
    )
