# Copyright 2026 ODYSS.AI AG
# SPDX-License-Identifier: Apache-2.0
#
# See the NOTICE file for attribution information.
#
# Author:
# Aleksander Bydłowski
# abydlowski@theodyss.ai
# aleksander.bydlowski@gmail.com
# core/config/resolver.py

import inspect

from typing import Any

from jinja2 import StrictUndefined
from jinja2.nativetypes import NativeEnvironment


from odyss_ai_flows.core.config.providers import (
    RenderContext,
    ProviderDef,
    REF,
    get_providers,
)

from odyss_ai_flows.core.config.tree import ConfigNode
from odyss_ai_flows.core.config.utils import SensitiveValue


# ---------------------------------------------------------
# Exceptions
# ---------------------------------------------------------

class InvalidReferenceCompositionError(RuntimeError):
    pass

# ---------------------------------------------------------
# Semantic template cache
# ---------------------------------------------------------

_semantic_template_cache: dict[str, Any] = {}


def clear_semantic_template_cache() -> None:
    _semantic_template_cache.clear()


# ---------------------------------------------------------
# Heuristics
# ---------------------------------------------------------

def looks_like_jinja(s: str) -> bool:
    return any(token in s for token in ("{{", "{%", "{#"))


def _needs_resolution(val: Any) -> bool:

    if isinstance(val, str):
        return looks_like_jinja(val)

    if isinstance(val, list):
        return any(_needs_resolution(v) for v in val)

    if isinstance(val, dict):
        return any(_needs_resolution(v) for v in val.values())

    return False


# ---------------------------------------------------------
# Provider binding
# ---------------------------------------------------------

def _bind_provider(
    provider_name: str,
    provider_def,
    ctx: RenderContext,
):

    async def wrapper(*args, **kwargs):

        # ---------------------------------------------------------
        # Semantic tracking
        # ---------------------------------------------------------

        if provider_name == "REF":
            ctx.ref_used = True
        else:
            ctx.non_ref_used = True

        # ---------------------------------------------------------
        # Sensitive tracking
        # ---------------------------------------------------------

        if provider_def.sensitive:
            ctx.mark_sensitive()

        # ---------------------------------------------------------
        # Provider execution
        # ---------------------------------------------------------

        result = provider_def.fn(*args, **kwargs)

        if inspect.isawaitable(result):
            return await result

        return result

    return wrapper


# ---------------------------------------------------------
# Jinja environment
# ---------------------------------------------------------

def _build_env(
    ctx: RenderContext,
) -> NativeEnvironment:

    env = NativeEnvironment(
        enable_async=True,
        undefined=StrictUndefined,
    )

    providers = dict(get_providers())

    for provider_name, provider_def in providers.items():

        env.globals[provider_name] = _bind_provider(
            provider_name,
            provider_def,
            ctx,
        )

    # ---------------------------------------------------------
    # Explicit REF injection
    # ---------------------------------------------------------

    env.globals["REF"] = _bind_provider(
        "REF",
        ProviderDef(fn=REF),
        ctx,
    )

    return env


# ---------------------------------------------------------
# Semantic validation
# ---------------------------------------------------------

def _validate_render_semantics(
    ctx: RenderContext,
) -> None:

    if ctx.ref_used and ctx.non_ref_used:

        raise InvalidReferenceCompositionError(
            "REF cannot be mixed with non-REF providers "
            "within the same config entry."
        )


# ---------------------------------------------------------
# Single entrypoint
# ---------------------------------------------------------

async def resolve(
    val: Any) -> Any:
    """
    Semantic config resolution entrypoint.

    Responsibilities:
    - recursive traversal
    - Jinja rendering
    - semantic provider tracking
    - semantic validation
    - semantic template caching

    Does NOT:
    - traverse config graph references
    - resolve REF recursively
    - apply scope semantics
    """

    # ---------------------------------------------------------
    # Primitive passthrough
    # ---------------------------------------------------------

    if not isinstance(val, (str, list, dict)):
        return val

    # ---------------------------------------------------------
    # String
    # ---------------------------------------------------------

    if isinstance(val, str):

        if not looks_like_jinja(val):
            return val

        # ---------------------------------------------------------
        # Semantic template cache
        # ---------------------------------------------------------

        if val in _semantic_template_cache:
            return _semantic_template_cache[val]

        # ---------------------------------------------------------
        # Render
        # ---------------------------------------------------------

        ctx = RenderContext()

        env = _build_env(ctx)

        template = env.from_string(val)

        result = await template.render_async()

        # ---------------------------------------------------------
        # Semantic validation
        # ---------------------------------------------------------

        _validate_render_semantics(ctx)

        # ---------------------------------------------------------
        # Sensitive wrapping
        # ---------------------------------------------------------

        if ctx.sensitive_used and isinstance(result, str):
            result = SensitiveValue(result)

        # ---------------------------------------------------------
        # Cache semantic result
        # ---------------------------------------------------------

        _semantic_template_cache[val] = result

        return result

    # ---------------------------------------------------------
    # List
    # ---------------------------------------------------------

    if isinstance(val, list):

        if not _needs_resolution(val):
            return val

        return [
            await resolve(
                v            )
            for v in val
        ]

    # ---------------------------------------------------------
    # Dict
    # ---------------------------------------------------------

    if isinstance(val, dict):

        if not _needs_resolution(val):
            return val

        return {
            k: await resolve(
                v            )
            for k, v in val.items()
        }

    return val


# ---------------------------------------------------------
# Config tree pre-resolution
# ---------------------------------------------------------

async def resolve_config_async(config) -> None:
    """
    Pre-resolve / pre-compile config tree in-place.

    This mutates the flow-local config tree into a fully
    operational representation optimized for runtime reads.
    """

    async def walk(node: ConfigNode):

        for k, v in list(node.config.items()):

            resolved = await resolve(
                v
            )

            resolved = await config._resolve_references(
                resolved,
                node_scope=node.path_str,
            )

            node.config[k] = resolved

        for child in node.children.values():
            await walk(child)

    await walk(config.root)