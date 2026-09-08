from odyss_ai_flows_token_limiter.middleware import token_limiter
from odyss_ai_flows_token_limiter.redis_factory import (
    get_redis_client,
    reset_redis_client,
    set_redis_client,
)
from odyss_ai_flows_token_limiter.store import (
    TokenLimitExceeded,
    clean_all_token_counters,
    get_all_token_counters,
    get_raw_token_counters,
    get_tokens_left,
)


def register(register_middleware) -> None:
    """Wire this middleware into the framework. Call from host bootstrap:

        from odyss_ai_flows.core.handlers.middleware.middleware import register_middleware
        import odyss_ai_flows_token_limiter
        odyss_ai_flows_token_limiter.register(register_middleware)

    Then select it in config: {"middleware": ["token_limiter"]}.
    """
    register_middleware("token_limiter", token_limiter)


__all__ = [
    "token_limiter",
    "register",
    "TokenLimitExceeded",
    "get_redis_client",
    "set_redis_client",
    "reset_redis_client",
    "get_all_token_counters",
    "get_raw_token_counters",
    "get_tokens_left",
    "clean_all_token_counters",
]
