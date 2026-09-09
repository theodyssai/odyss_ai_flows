from typing import Optional, Tuple

from openai import AsyncOpenAI


_DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"

_client_cache: dict[
    Tuple[str, bool],
    AsyncOpenAI,
] = {}


def get_openrouter_client(
    api_key: str,
    base_url: Optional[str] = None,
) -> AsyncOpenAI:
    base_url = (base_url or _DEFAULT_BASE_URL).rstrip("/")

    cache_key = (
        base_url,
        bool(api_key),
    )

    if cache_key in _client_cache:
        return _client_cache[cache_key]

    client = AsyncOpenAI(
        base_url=base_url,
        api_key=api_key,
    )

    _client_cache[cache_key] = client

    return client
