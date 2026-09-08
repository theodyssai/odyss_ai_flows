# Copyright 2026 ODYSS.AI AG
# SPDX-License-Identifier: Apache-2.0
#
# See the NOTICE file for attribution information.
#
# Author:
# Aleksander Bydłowski
# abydlowski@theodyss.ai
# ai@bydlow.ski
from typing import Optional, Tuple

from openai import AsyncAzureOpenAI
from azure.identity import (
    DefaultAzureCredential,
    get_bearer_token_provider,
)


_client_cache: dict[
    Tuple[str, str, str],
    AsyncAzureOpenAI,
] = {}

_credential: DefaultAzureCredential | None = None


def _get_credential() -> DefaultAzureCredential:
    global _credential

    if _credential is None:
        _credential = DefaultAzureCredential()

    return _credential


def get_azure_openai_client(
    endpoint: str,
    api_version: str,
    api_key: Optional[str] = None,
) -> AsyncAzureOpenAI:
    endpoint = endpoint.rstrip("/")

    auth_mode = (
        "api_key"
        if api_key
        else "entra"
    )

    cache_key = (
        endpoint,
        api_version,
        auth_mode,
    )

    if cache_key in _client_cache:
        return _client_cache[
            cache_key
        ]

    if api_key:
        client = AsyncAzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=endpoint,
        )

    else:
        token_provider = get_bearer_token_provider(
            _get_credential(),
            "https://ai.azure.com/.default",
        )

        client = AsyncAzureOpenAI(
            api_version=api_version,
            azure_endpoint=endpoint,
            azure_ad_token_provider=token_provider,
        )

    _client_cache[
        cache_key
    ] = client

    return client