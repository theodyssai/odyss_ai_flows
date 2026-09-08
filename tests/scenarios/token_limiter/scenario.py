from __future__ import annotations

import fakeredis.aioredis as fakeredis
from types import SimpleNamespace
from typing import Any, Optional

from odyss_ai_flows.core.handlers.llm.components.base import (
    LLMHandlerComponent,
)
from odyss_ai_flows.core.handlers.llm.registry import (
    register_handler_component,
)
from odyss_ai_flows.core.handlers.middleware.middleware import (
    register_middleware,
)
from odyss_ai_flows.core.runtime.prepared_flow import PreparedFlow
from odyss_ai_flows.core.runtime.runner import run_flow

from odyss_ai_flows_token_limiter import register, set_redis_client

from tests.tests_runtime.assertions import (
    assert_flow_failure,
    assert_flow_success,
)


# This scenario exercises the middleware against the real ComposedHandler
# pipeline with a fake caller and an in-memory fakeredis - no network, no
# credentials, no live Redis.
REQUIRES_LLM = False


# =================================================
# Fake caller: sets handler.response like AzureCaller
# =================================================

class FakeCaller(LLMHandlerComponent):
    async def run(self, _: Optional[str]) -> Any:
        self.handler.response = SimpleNamespace(
            usage=SimpleNamespace(
                prompt_tokens=10,
                completion_tokens=5,
                total_tokens=15,
            )
        )
        return "ok"


def _tree(token_limiter_cfg: dict) -> dict:
    return {
        "name": "",
        "path": ".",
        "config": {
            "middleware": ["token_limiter"],
            "token_limiter": token_limiter_cfg,
            "llm": {
                "pipeline": "fake",
                "pipelines": {"fake": ["fake_caller"]},
            },
        },
        "children": {},
    }


def _llm_flow(token_limiter_cfg: dict) -> PreparedFlow:
    tree = _tree(token_limiter_cfg)
    return PreparedFlow(config_tree=tree).fset("llm.jinja2", "ignored")


# Register middleware + the fake caller once per (isolated) subprocess.
register(register_middleware)
register_handler_component("fake_caller", FakeCaller)

# Back the store with an in-memory fakeredis for the whole scenario.
_redis = fakeredis.FakeRedis(decode_responses=True)
set_redis_client(_redis)


async def run_scenario():

    # =============================================
    # 1. Data exposure: usage recorded after the node runs
    # =============================================

    await _redis.flushdb()

    generous = {
        "general": {
            "input": {"minute": 1_000_000},
            "output": {"minute": 1_000_000},
        },
        "deployment": {
            "input": {"minute": 1_000_000},
            "output": {"minute": 1_000_000},
        },
    }

    result = await run_flow(
        _llm_flow(generous),
        provided_tree=_tree(generous),
    )

    assert_flow_success(result)

    # The middleware read handler.response.usage *after* node execution,
    # across both scopes and both directions, and wrote it to Redis.
    assert float((await _redis.hgetall("input_tokens:general:minute"))["used"]) == 10
    assert float((await _redis.hgetall("input_tokens:default:minute"))["used"]) == 10
    assert float((await _redis.hgetall("output_tokens:general:minute"))["used"]) == 5
    assert float((await _redis.hgetall("output_tokens:default:minute"))["used"]) == 5

    # =============================================
    # 2. Preflight enforcement: over-limit -> failure
    # =============================================

    await _redis.flushdb()

    tiny = {
        "general": {"input": {"minute": 1}},
    }

    # First run fills the bucket (used=10 > limit=1).
    first = await run_flow(_llm_flow(tiny), provided_tree=_tree(tiny))
    assert_flow_success(first)

    # Second run trips the preflight check.
    second = await run_flow(
        _llm_flow(tiny),
        provided_tree=_tree(tiny),
        raise_on_fail=False,
    )
    assert_flow_failure(second)
    assert "Token limit exceeded" in str(second.error)

    # =============================================
    # 3. soft_limit: warn instead of raise
    # =============================================

    await _redis.flushdb()

    soft = {
        "soft_limit": True,
        "general": {"input": {"minute": 1}},
    }

    s_first = await run_flow(_llm_flow(soft), provided_tree=_tree(soft))
    assert_flow_success(s_first)

    s_second = await run_flow(
        _llm_flow(soft),
        provided_tree=_tree(soft),
        raise_on_fail=False,
    )
    assert_flow_success(s_second)

    # =============================================
    # 4. Non-LLM node: no .response -> no-op
    # =============================================

    await _redis.flushdb()

    async def py_node():
        return "done"

    py_tree = _tree(generous)
    py_flow = PreparedFlow(config_tree=py_tree).fset("plain.py", py_node)

    py_result = await run_flow(py_flow, provided_tree=py_tree)
    assert_flow_success(py_result)
    assert await _redis.keys("*") == []
