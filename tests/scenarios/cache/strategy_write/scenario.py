from __future__ import annotations

import tempfile
from pathlib import Path


async def run_scenario():
    from odyss_ai_flows_cache import cache_middleware
    from odyss_ai_flows.core.handlers.middleware.middleware import register_middleware
    from odyss_ai_flows.core.runtime.prepared_flow import PreparedFlow
    from odyss_ai_flows.core.runtime.runner import run_flow
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
            "cache": {"strategy": "write", "dir": cache_dir},
        },
        "children": {},
    }
    flow = PreparedFlow(config_tree=tree).fset("node.py", node)

    r1 = await run_flow(flow, provided_tree=tree)
    r2 = await run_flow(flow, provided_tree=tree)

    assert calls["n"] == 2, f"strategy=write must run every time, got {calls['n']} calls"

    cache_files = list(Path(cache_dir).rglob("*.json"))
    assert len(cache_files) == 1, f"expected 1 cache file, found {len(cache_files)}"

    # second run overwrites — file should contain the latest result
    import json
    cached = json.loads(cache_files[0].read_text())
    assert cached == 2, f"cache file should hold the latest result (2), got {cached!r}"
