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
from typing import List

from importlib.metadata import entry_points

from odyss_ai_flows.core.handlers.llm.registry import (
    HANDLER_COMPONENT_REGISTRY,
)
from odyss_ai_flows.core.handlers.llm.registry import (
    _load_plugin_components,
)


# =========================================================
# Minimal core fallback pipelines
# =========================================================

DEFAULT_PIPELINES: Dict[
    str,
    List[str],
] = {
    "default": [
        "render",
    ],

    "structured": [
        "render",
    ],
}


# =========================================================
# Plugin pipelines
# =========================================================

_PIPELINES_LOADED = False

_PLUGIN_PIPELINES: Dict[
    str,
    List[str],
] = {}


def _load_plugin_pipelines():
    global _PIPELINES_LOADED

    if _PIPELINES_LOADED:
        return

    try:
        eps = entry_points(
            group="odyss_ai_flows.llm_pipelines"
        )

    except TypeError:
        eps = entry_points().get(
            "odyss_ai_flows.llm_pipelines",
            [],
        )

    for ep in eps:
        fn = ep.load()

        pipelines = fn()

        if not isinstance(
            pipelines,
            dict,
        ):
            raise ValueError(
                f"Pipeline entry point "
                f"'{ep.name}' must return "
                f"dict[str, list[str]]"
            )

        _PLUGIN_PIPELINES.update(
            pipelines
        )

    _PIPELINES_LOADED = True


# =========================================================
# Resolution
# =========================================================

def resolve_pipeline(
    pipeline_name: str | None,
    model_present: bool,
    user_pipelines: dict[str, list[str]],
) -> list[str]:

    _load_plugin_pipelines()
    _load_plugin_components()

    # -----------------------------------------------------
    # Determine effective pipeline name
    # -----------------------------------------------------

    if pipeline_name is None:

        if "azure_default" in _PLUGIN_PIPELINES:
            effective_name = "azure_default"

        else:
            effective_name = (
                "structured"
                if model_present
                else "default"
            )

    else:
        effective_name = pipeline_name

    # -----------------------------------------------------
    # Resolve pipeline source
    # -----------------------------------------------------

    if effective_name in user_pipelines:
        keys = list(
            user_pipelines[
                effective_name
            ]
        )

    elif effective_name in _PLUGIN_PIPELINES:
        keys = list(
            _PLUGIN_PIPELINES[
                effective_name
            ]
        )

    elif effective_name in DEFAULT_PIPELINES:
        keys = list(
            DEFAULT_PIPELINES[
                effective_name
            ]
        )

    else:
        raise ValueError(
            f"Unknown pipeline: "
            f"{effective_name}"
        )

    # -----------------------------------------------------
    # Validation
    # -----------------------------------------------------

    if not keys:
        raise ValueError(
            f"Pipeline "
            f"'{effective_name}' is empty"
        )

    for k in keys:
        if (
            k
            not in HANDLER_COMPONENT_REGISTRY
        ):
            raise ValueError(
                f"Pipeline "
                f"'{effective_name}' "
                f"references unknown "
                f"component '{k}'. "
                f"Known components: "
                f"{sorted(HANDLER_COMPONENT_REGISTRY.keys())}"
            )

    return keys