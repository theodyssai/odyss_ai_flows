from __future__ import annotations

import json
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
        return {"value": 42, "call": calls["n"]}

    cache_dir = tempfile.mkdtemp()
    tree = {
        "name": "", "path": ".",
        "config": {
            "middleware": ["cache"],
            "cache": {"strategy": "both", "dir": cache_dir},
        },
        "children": {},
    }
    flow = PreparedFlow(config_tree=tree).fset("node.py", node)

    r1 = await run_flow(flow, provided_tree=tree)
    r2 = await run_flow(flow, provided_tree=tree)

    assert calls["n"] == 1, \
        f"strategy=both must skip node on cache hit, but body ran {calls['n']} times"
    assert r1["node"] == r2["node"], \
        f"both runs must return the same result: {r1['node']!r} vs {r2['node']!r}"

    cache_files = list(Path(cache_dir).rglob("*.json"))
    assert len(cache_files) == 1, f"expected 1 cache file, found {len(cache_files)}"
    assert json.loads(cache_files[0].read_text()) == {"value": 42, "call": 1}
