from __future__ import annotations

import os
from pathlib import Path

import fakeredis.aioredis as fakeredis
from dotenv import load_dotenv

from odyss_ai_flows.core.handlers.middleware.middleware import (
    register_middleware,
)
from odyss_ai_flows.core.runtime.runner import run_flow

from odyss_ai_flows_token_limiter import register, set_redis_client

from tests.tests_runtime.assertions import assert_flow_success


# Real `.jinja2` node through azure_default -> auto-classified as needing a
# model; runs only when Azure config resolves, skips otherwise. The token store
# is backed by an in-memory fakeredis so the test needs no live Redis server.

register(register_middleware)


async def run_scenario():

    load_dotenv(Path(__file__).parent / ".env.local", override=True)

    redis = fakeredis.FakeRedis(decode_responses=True)
    set_redis_client(redis)
    await redis.flushdb()

    result = await run_flow("reply_flow")

    assert_flow_success(result)

    # The deployment scope is keyed by the connection's deployment_name.
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "default")

    # A genuine response.usage flowed through the middleware after the node ran.
    input_used = 0.0
    for key in await redis.keys(f"input_tokens:{deployment}:*"):
        used = (await redis.hgetall(key)).get("used", 0)
        input_used += float(used)

    assert input_used > 0, (
        f"expected non-zero recorded input tokens for deployment "
        f"'{deployment}', got keys: {await redis.keys('*')}"
    )
