from __future__ import annotations

from pathlib import Path

import networkx as nx

from odyss_ai_flows.core.utils.flow_graph import build_flow_graph


def build_dag(flow_name: str) -> nx.DiGraph:
    return build_flow_graph(Path(flow_name))
