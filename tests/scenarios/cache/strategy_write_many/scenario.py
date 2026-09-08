from __future__ import annotations

import json
import tempfile
from pathlib import Path


async def run_scenario():
    from odyss_ai_flows_cache import cache_middleware
    from odyss_ai_flows.core.handlers.middleware.middleware import register_middleware
    from odyss_ai_flows.core.runtime.prepared_flow import PreparedFlow
    from odyss_ai_flows.core.runtime.runner import run_flow
    from odyss_ai_flows.core.runtime.run_context import current_top_run_id
    register_middleware("cache", cache_middleware)

    calls = {"n": 0}

    async def node():
        calls["n"] += 1
        return calls["n"]

    cache_dir = tempfile.mkdtemp()
    tree = {
        "name": "", "path": ".",
        "config": {
            "middleware": ["cache"],
            "cache": {"strategy": "write_many", "dir": cache_dir},
        },
        "children": {},
    }
    flow = PreparedFlow(config_tree=tree).fset("node.py", node)

    # Both calls share the same run_id because ensure_top_run_state runs in the
    # calling coroutine's context before create_task, so the second call finds
    # RUN_STATE already set and reuses the same id.
    await run_flow(flow, provided_tree=tree)
    run_id = current_top_run_id()
    await run_flow(flow, provided_tree=tree)

    assert calls["n"] == 2, \
        f"strategy=write_many must always run the node, got {calls['n']} calls"

    # Cache is nested under a per-run, timestamped subdirectory (not flat like
    # strategy=write). Name format mirrors old-flows: "%Y%m%d_%H%M%S_<short>".
    run_dirs = [p for p in Path(cache_dir).iterdir() if p.is_dir()]
    assert len(run_dirs) == 1, f"expected 1 per-run subdirectory, found {run_dirs}"

    run_dir = run_dirs[0]
    assert run_dir.name.endswith(run_id[:8]), \
        f"subdir name {run_dir.name!r} should end with run_id prefix {run_id[:8]!r}"

    flat_files = [p for p in Path(cache_dir).iterdir() if p.is_file()]
    assert not flat_files, \
        f"write_many must not write flat files, found: {flat_files}"

    cache_files = list(run_dir.rglob("*.json"))
    assert len(cache_files) == 1, \
        f"expected 1 cache file in run dir, found {len(cache_files)}"

    # second write overwrites the first — file holds the latest result
    assert json.loads(cache_files[0].read_text()) == 2
