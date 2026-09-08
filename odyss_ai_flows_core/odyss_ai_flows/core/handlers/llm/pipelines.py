# Copyright 2026 ODYSS.AI AG
# SPDX-License-Identifier: Apache-2.0
#
# See the NOTICE file for attribution information.
#
# Author:
# Aleksander Bydłowski
# abydlowski@theodyss.ai
# ai@bydlow.ski
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
from odyss_ai_flows.core.handlers.llm.registry import (
    _plugin_prefix,
)
from odyss_ai_flows.core.handlers.llm.registry import (
    resolve_component_key,
)
from odyss_ai_flows.core.utils.logger import (
    logger,
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


def _qualify(prefix: str, comp: str) -> str:
    key = f"{prefix}.{comp}"

    return (
        key
        if key in HANDLER_COMPONENT_REGISTRY
        else comp
    )


def _load_plugin_pipelines():
    global _PIPELINES_LOADED

    if _PIPELINES_LOADED:
        return

    _load_plugin_components()

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
        # Isolate a broken plugin: any failure loading or calling one
        # entry point must not prevent the others from registering.
        try:
            fn = ep.load()
            pipelines = fn()

        except Exception as exc:
            logger.warning(
                f"Skipping LLM pipeline "
                f"'{ep.name}' ({ep.value}): "
                f"{exc!r}"
            )

            continue

        if not isinstance(
            pipelines,
            dict,
        ):
            logger.warning(
                f"Skipping LLM pipeline "
                f"'{ep.name}' ({ep.value}): "
                f"must return dict[str, list[str]], "
                f"got {type(pipelines).__name__}"
            )

            continue

        prefix = _plugin_prefix(ep)

        for name, comps in pipelines.items():
            _PLUGIN_PIPELINES[f"{prefix}.{name}"] = [
                _qualify(prefix, c)
                for c in comps
            ]

    _PIPELINES_LOADED = True


def _match_plugin_pipeline(name: str) -> list[str]:
    if name in _PLUGIN_PIPELINES:
        return [name]

    suffix = "." + name

    return [
        k
        for k in _PLUGIN_PIPELINES
        if k.endswith(suffix)
    ]


def _plugin_default_pipeline() -> str | None:
    by_plugin: dict[str, list[str]] = {}

    for key in _PLUGIN_PIPELINES:
        prefix = key.partition(".")[0]
        by_plugin.setdefault(
            prefix,
            [],
        ).append(key)

    candidates: list[str] = []

    for keys in by_plugin.values():
        if len(keys) == 1:
            candidates.append(keys[0])
            continue

        defaults = [
            k
            for k in keys
            if k.partition(".")[2].endswith(
                "_default"
            )
        ]

        if len(defaults) == 1:
            candidates.append(defaults[0])

        else:
            # 0 or >1 '_default' -> alphabetical
            # fallback within plugin
            candidates.append(sorted(keys)[0])

    if not candidates:
        return None

    return sorted(candidates)[0]


# =========================================================
# Resolution
# =========================================================

def resolve_pipeline(
    pipeline_name: str | None,
    model_present: bool,
    user_pipelines: dict[str, list[str]],
) -> tuple[str, list[str]]:

    _load_plugin_pipelines()
    _load_plugin_components()

    # -----------------------------------------------------
    # Determine effective pipeline name
    # -----------------------------------------------------

    if pipeline_name is None:

        plugin_default = _plugin_default_pipeline()

        if plugin_default is not None:
            effective_name = plugin_default

        else:
            effective_name = (
                "structured"
                if model_present
                else "default"
            )

    else:
        effective_name = pipeline_name

    # -----------------------------------------------------
    # Resolve pipeline source (user -> plugin -> default)
    # -----------------------------------------------------

    if effective_name in user_pipelines:
        keys = list(
            user_pipelines[
                effective_name
            ]
        )

    else:
        matches = _match_plugin_pipeline(
            effective_name
        )

        if len(matches) == 1:
            keys = list(
                _PLUGIN_PIPELINES[
                    matches[0]
                ]
            )

        elif len(matches) > 1:
            raise ValueError(
                f"Ambiguous pipeline "
                f"'{effective_name}', "
                f"defined by multiple plugins: "
                f"{sorted(matches)}. "
                f"Reference it with its plugin "
                f"prefix (e.g. '{matches[0]}')."
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

    resolved: list[str] = []

    for k in keys:
        try:
            resolved.append(
                resolve_component_key(k)
            )

        except ValueError as exc:
            raise ValueError(
                f"Pipeline "
                f"'{effective_name}': {exc}"
            ) from exc

    return effective_name, resolved