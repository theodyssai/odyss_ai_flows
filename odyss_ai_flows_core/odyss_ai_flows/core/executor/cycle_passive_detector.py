# Copyright 2026 ODYSS.AI AG
# SPDX-License-Identifier: Apache-2.0
#
# See the NOTICE file for attribution information.
import networkx as nx

from odyss_ai_flows.core.utils.flow_graph import build_graph_from_structure
from odyss_ai_flows.core.builder.types import FlowStructure
from odyss_ai_flows.core.utils.logger import logger


def analyze_cycles(structure: FlowStructure) -> None:
    graph = build_graph_from_structure(structure)

    for cycle in nx.simple_cycles(graph):
        logger.warning(
            "Possible dependency cycle: %s",
            " -> ".join(cycle + [cycle[0]]),
        )
