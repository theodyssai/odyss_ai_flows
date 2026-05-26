# Copyright 2026 ODYSS.AI AG
# SPDX-License-Identifier: Apache-2.0
#
# See the NOTICE file for attribution information.
#
# Author:
# Aleksander Bydłowski
# abydlowski@theodyss.ai
# aleksander.bydlowski@gmail.com
# core/config/providers.py

import os

from dataclasses import dataclass
from typing import Any, Callable, Dict


# ---------------------------------------------------------
# Semantic objects
# ---------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ConfigReference:
    path: str


# ---------------------------------------------------------
# Render context
# ---------------------------------------------------------

class RenderContext:

    def __init__(self):

        # ---------------------------------------------------------
        # Sensitive semantics
        # ---------------------------------------------------------

        self.sensitive_used: bool = False

        # ---------------------------------------------------------
        # REF semantics
        # ---------------------------------------------------------

        self.ref_used: bool = False

        # ---------------------------------------------------------
        # Non-REF semantics
        # ---------------------------------------------------------

        self.non_ref_used: bool = False

    def mark_sensitive(self) -> None:
        self.sensitive_used = True


# ---------------------------------------------------------
# Provider definition
# ---------------------------------------------------------

@dataclass(slots=True)
class ProviderDef:
    fn: Callable[..., Any]
    sensitive: bool = False


# ---------------------------------------------------------
# Provider registry
# ---------------------------------------------------------

_providers: Dict[str, ProviderDef] = {}


def register_provider(
    name: str,
    provider: Callable[..., Any],
    *,
    sensitive: bool = False,
) -> None:

    _providers[name] = ProviderDef(
        fn=provider,
        sensitive=sensitive,
    )


def get_providers() -> Dict[str, ProviderDef]:
    return _providers


def clear_providers() -> None:
    _providers.clear()


# ---------------------------------------------------------
# Built-in providers
# ---------------------------------------------------------

async def ENV(key: str) -> Any:
    return os.environ.get(key)


async def LITERAL_SECRET(value: str) -> Any:
    return value


async def REF(path: str) -> ConfigReference:
    """
    REF returns semantic redirect object.

    Recursive traversal is handled later by ConfigManager.
    """

    return ConfigReference(path)


# ---------------------------------------------------------
# Bootstrap providers
# ---------------------------------------------------------

async def SECRET(key: str) -> Any:

    from odyss_ai_flows_azure.config.config_providers import (
        AzureSecretProvider,
    )

    register_provider(
        "SECRET",
        AzureSecretProvider(),
        sensitive=True,
    )

    provider = _providers["SECRET"]

    result = provider.fn(key)

    if hasattr(result, "__await__"):
        return await result

    return result


async def CONFIG(key: str) -> Any:

    from odyss_ai_flows_azure.config.config_providers import (
        AzureConfigProvider,
    )

    register_provider(
        "CONFIG",
        AzureConfigProvider(),
    )

    provider = _providers["CONFIG"]

    result = provider.fn(key)

    if hasattr(result, "__await__"):
        return await result

    return result


# ---------------------------------------------------------
# Import-time bootstrap
# ---------------------------------------------------------

register_provider(
    "ENV",
    ENV,
)

register_provider(
    "LITERAL_SECRET",
    LITERAL_SECRET,
    sensitive=True,
)

register_provider(
    "REF",
    REF,
)

register_provider(
    "SECRET",
    SECRET,
    sensitive=True,
)

register_provider(
    "CONFIG",
    CONFIG,
)