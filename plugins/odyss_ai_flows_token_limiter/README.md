# odyss_ai_flows_token_limiter

Internal middleware plugin that enforces **token-usage limits** around LLM node execution,
using a **Redis-backed** leaky-bucket store. It is a refactor of the former `_execute` monkey
patch into the framework's first-class middleware layer, keeping Redis as the shared counter
store so limits hold across processes and serverless workers.

## How it works

The middleware wraps node execution:

1. **Preflight** — before the node runs, it reads the counters from Redis and raises
   `TokenLimitExceeded` if any configured limit is already exceeded (the node fails).
2. **Record** — after the node runs, it reads `handler.response.usage` (set by the LLM
   caller component) and updates the counters with `prompt_tokens` (`input`) and
   `completion_tokens` (`output`).

Counters are decay-based leaky buckets stored as Redis hashes keyed
`"{direction}_tokens:{scope_id}:{window}"`, holding `{used, last_updated}`. Each bucket drains
at `limit / window_size` tokens per second (capacity `limit`). The post-call update runs as an
atomic `EVALSHA` Lua script (loaded once, its SHA cached in Redis) so concurrent workers
decay-and-increment without races. Limits are tracked across two **directions**
(`input`/`output`), two **scopes** (`general` shared + `deployment` per-deployment), and any
configured **windows** (`second`/`minute`/`hour`/`day`/`week`/`month`).

Usage is read by duck-typing `handler.response.usage`, so the plugin is provider-agnostic and
does not import the Azure plugin. Nodes without a `response` (e.g. Python nodes) are a no-op.

## Installation

```bash
cd odyss_ai
pip install -e plugins/odyss_ai_flows_token_limiter
```

This pulls in `redis`. For tests, install the `test` extra (adds `fakeredis`):

```bash
pip install -e "plugins/odyss_ai_flows_token_limiter[test]"
```

## Registration

Middleware is not auto-discovered. Register it once at host bootstrap:

```python
from odyss_ai_flows.core.handlers.middleware.middleware import register_middleware
import odyss_ai_flows_token_limiter
odyss_ai_flows_token_limiter.register(register_middleware)
```

## Configuration

Select the middleware and configure limits in any scoped `config.json` (global/flow/folder/node).
The Redis connection is read from a sibling `redis` block (defaults to `localhost:6379`):

```jsonc
{
  "middleware": ["token_limiter"],
  "redis": {
    "host": "localhost",   // remote host -> TLS + access_key auth
    "port": 6379,
    "access_key": null     // required when host != "localhost"
  },
  "token_limiter": {
    "soft_limit": false,                                  // true -> warn instead of raise
    "general":    { "input": { "minute": 100000 }, "output": { "minute": 50000 } },
    "deployment": { "input": { "minute": 40000  }, "output": { "minute": 20000 } }
  }
}
```

When the `token_limiter` block is absent the middleware passes through. The Redis client is
created lazily and cached as a process-wide singleton.

## Inspection

The counters live in Redis and can be read back with the store helpers (each takes the active
`redis_client`, e.g. from `get_redis_client`):

```python
from odyss_ai_flows_token_limiter import get_redis_client, get_raw_token_counters, get_tokens_left

client = await get_redis_client(redis_config)
await get_raw_token_counters("gpt-4o", cfg, client)  # raw {used, last_updated} per key
await get_tokens_left("gpt-4o", cfg, client)         # remaining tokens per direction/scope/window
```

For tests, inject an in-memory client with `set_redis_client(fakeredis.aioredis.FakeRedis(decode_responses=True))`
(`reset_redis_client()` clears the cached singleton).
