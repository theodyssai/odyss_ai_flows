# Copyright 2026 ODYSS.AI AG
# SPDX-License-Identifier: Apache-2.0
#
# See the NOTICE file for attribution information.
#
# Author:
# Aleksander Bydłowski
# abydlowski@theodyss.ai
# ai@bydlow.ski
from pathlib import Path

from odyss_ai_flows.core.utils.logger import logger
from odyss_ai_flows.core.builder.types import FlowNode, FlowStructure
from odyss_ai_flows.core.builder.registry import get_node_kinds, get_handler
from odyss_ai_flows.core.files.api import fget
from odyss_ai_flows.core.config.api import cget


async def build_and_initialize_structure(base_path: Path) -> FlowStructure:
    nodes: dict[str, FlowNode] = {}

    logger.debug(f"[builder] Building flow structure from: {base_path}")

    # ---------------------------------------------------------
    # discovery phase
    # ---------------------------------------------------------
    discovered = []

    for kind in get_node_kinds():
        entries = fget(f"node:{kind}")

        for entry in entries:
            if not entry.name:
                raise ValueError(
                    f"[builder] Missing node name in entry: {entry}"
                )

            if entry.name in nodes:
                raise ValueError(
                    f"[builder] Duplicate node name '{entry.name}' "
                    f"(kind={kind}, entry={entry})"
                )

            node = FlowNode(entry=entry)

            nodes[entry.name] = node
            discovered.append((entry.name, kind, entry.rebased_path))

    if discovered:
        logger.debug("[builder] Discovered nodes:")
        for name, kind, path in discovered:
            logger.debug(f"  - {name} ({kind}) @ {path}")

    # ---------------------------------------------------------
    # handler assignment phase
    # ---------------------------------------------------------
    for node in nodes.values():
        handler_type = await cget(
            "handler_type",
            default=node.kind,
            scope=node.scope,
        )

        try:
            handler_cls = get_handler(handler_type)
        except ValueError as e:
            raise ValueError(
                f"[builder] No handler registered for '{handler_type}' "
                f"(node='{node.name}', scope='{node.scope}')"
            ) from e

        node.handler = handler_cls(node=node)

    logger.debug(f"[builder] Total nodes initialized: {len(nodes)}")

    return FlowStructure(nodes=nodes, base_path=base_path)