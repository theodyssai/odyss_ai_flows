# Copyright 2026 ODYSS.AI AG
# SPDX-License-Identifier: Apache-2.0
#
# See the NOTICE file for attribution information.
#
# Author:
# Aleksander Bydłowski
# abydlowski@theodyss.ai
# aleksander.bydlowski@gmail.com
from __future__ import annotations

from typing import Dict
from typing import Type
from typing import Union

from importlib.metadata import entry_points

from odyss_ai_flows.core.handlers.llm.components.action_execute import (
    ActionExecuteComponent,
)
from odyss_ai_flows.core.handlers.llm.components.action_model import (
    ActionModelComponent,
)
from odyss_ai_flows.core.handlers.llm.components.base import (
    LLMHandlerComponent,
)
from odyss_ai_flows.core.handlers.llm.components.renderers import (
    PromptRenderer,
)
from odyss_ai_flows.core.utils.logger import (
    logger,
)


# =========================================================
# Core registry
# =========================================================

HANDLER_COMPONENT_REGISTRY: Dict[
    str,
    Type[LLMHandlerComponent],
] = {
    "render": PromptRenderer,

    # -----------------------------------------------------
    # Action system
    # -----------------------------------------------------

    "action_model": ActionModelComponent,
    "action_execute": ActionExecuteComponent,
}


# =========================================================
# Plugin loading
# =========================================================

_COMPONENTS_LOADED = False


def _plugin_prefix(ep) -> str:
    return (
        ep.value
        .partition(":")[0]
        .partition(".")[0]
    )


def _load_plugin_components():
    global _COMPONENTS_LOADED

    if _COMPONENTS_LOADED:
        return

    try:
        eps = entry_points(
            group="odyss_ai_flows.llm_components"
        )

    except TypeError:
        eps = entry_points().get(
            "odyss_ai_flows.llm_components",
            [],
        )

    for ep in eps:
        # Isolate a broken plugin: any failure loading one entry
        # point must not prevent the others from registering.
        try:
            cls = ep.load()

        except Exception as exc:
            logger.warning(
                f"Skipping LLM component "
                f"'{ep.name}' ({ep.value}): "
                f"{exc!r}"
            )

            continue

        HANDLER_COMPONENT_REGISTRY[
            f"{_plugin_prefix(ep)}.{ep.name}"
        ] = cls

    _COMPONENTS_LOADED = True


# =========================================================
# Public API
# =========================================================

def register_handler_component(
    name: str,
    cls: Type[LLMHandlerComponent],
) -> None:

    HANDLER_COMPONENT_REGISTRY[
        name
    ] = cls


def _namespaced_matches(name: str) -> list[str]:
    suffix = "." + name

    return [
        k
        for k in HANDLER_COMPONENT_REGISTRY
        if k.endswith(suffix)
    ]


def resolve_component_key(ref: str) -> str:
    if ref in HANDLER_COMPONENT_REGISTRY:
        return ref

    matches = _namespaced_matches(ref)

    if len(matches) == 1:
        return matches[0]

    if len(matches) > 1:
        raise ValueError(
            f"Ambiguous component '{ref}', "
            f"defined by multiple plugins: "
            f"{sorted(matches)}. "
            f"Reference it with its plugin "
            f"prefix (e.g. '{matches[0]}')."
        )

    raise ValueError(
        f"Unknown component '{ref}'. "
        f"Known components: "
        f"{sorted(HANDLER_COMPONENT_REGISTRY.keys())}"
    )


def resolve_component_class(
    ref: Union[
        str,
        Type[LLMHandlerComponent],
    ]
) -> Type[LLMHandlerComponent]:

    if isinstance(ref, str):
        _load_plugin_components()

        return HANDLER_COMPONENT_REGISTRY[
            resolve_component_key(ref)
        ]

    return ref