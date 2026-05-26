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
        cls = ep.load()

        HANDLER_COMPONENT_REGISTRY[
            ep.name
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


def resolve_component_class(
    ref: Union[
        str,
        Type[LLMHandlerComponent],
    ]
) -> Type[LLMHandlerComponent]:

    if isinstance(ref, str):
        _load_plugin_components()

        if (
            ref
            not in HANDLER_COMPONENT_REGISTRY
        ):
            raise ValueError(
                f"Unknown component '{ref}'. "
                f"Known components: "
                f"{sorted(HANDLER_COMPONENT_REGISTRY.keys())}"
            )

        return HANDLER_COMPONENT_REGISTRY[
            ref
        ]

    return ref