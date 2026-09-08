# Copyright 2026 ODYSS.AI AG
# SPDX-License-Identifier: Apache-2.0
#
# See the NOTICE file for attribution information.
from pathlib import Path

import networkx as nx

from odyss_ai_flows.core.utils.flow_graph import build_flow_graph
from odyss_ai_flows.core.utils.logger import logger

_COL_NODE = 10
_COL_DEPS = 16
_COL_FEEDS = 16


def inspect_flow(flow_path: Path | str) -> None:
    flow_path = Path(flow_path)
    graph = build_flow_graph(flow_path)

    cycles = list(nx.simple_cycles(graph))
    is_acyclic = not cycles

    cycle_label = "acyclic"
    if cycles:
        path = cycles[0]
        cycle_label = "(!) cycle: " + " -> ".join(path + [path[0]])

    node_count = graph.number_of_nodes()
    header = f"{flow_path.name}  |  {node_count} node{'s' if node_count != 1 else ''}  |  {cycle_label}"
    sep = "-" * len(header)

    print(header)
    print(sep)
    print(
        f"{'node':<{_COL_NODE}}{'depends on':<{_COL_DEPS}}{'needed by':<{_COL_FEEDS}}"
    )
    print(sep)

    if is_acyclic:
        order = list(nx.lexicographical_topological_sort(graph))
    else:
        order = sorted(graph.nodes())

    for node in order:
        deps = ", ".join(sorted(graph.successors(node))) or "-"
        feeds = ", ".join(sorted(graph.predecessors(node))) or "-"
        print(f"{node:<{_COL_NODE}}{deps:<{_COL_DEPS}}{feeds:<{_COL_FEEDS}}")
