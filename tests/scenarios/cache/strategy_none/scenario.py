from __future__ import annotations

import tempfile

from odyss_ai_flows.core.runtime.prepared_flow import PreparedFlow
from odyss_ai_flows.core.runtime.runner import run_flow


async def run_scenario():
    from odyss_ai_flows_cache import cache_middleware
    from odyss_ai_flows.core.handlers.middleware.middleware import register_middleware
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
            "cache": {"strategy": "none", "dir": cache_dir},
        },
        "children": {},
    }
    flow = PreparedFlow(config_tree=tree).fset("node.py", node)

    await run_flow(flow, provided_tree=tree)
    await run_flow(flow, provided_tree=tree)

    assert calls["n"] == 2, f"strategy=none must run every time, got {calls['n']} calls"
    assert not list(__import__("pathlib").Path(cache_dir).rglob("*.json")), \
        "strategy=none must not write any cache files"
