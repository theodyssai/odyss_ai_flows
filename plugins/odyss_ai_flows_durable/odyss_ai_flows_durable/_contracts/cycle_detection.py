from __future__ import annotations

import networkx as nx

from odyss_ai_flows_durable._contracts.exceptions import OrchestrationError
from odyss_ai_flows.core.utils.logger import logger


def assert_dag_acyclic(graph: nx.DiGraph, flow_name: str) -> None:
    cycles = list(nx.simple_cycles(graph))
    if not cycles:
        return

    path = cycles[0]
    raise OrchestrationError(
        f"Dependency cycle in flow '{flow_name}': {' -> '.join(path + [path[0]])}",
    )


def warn_if_subflow_cycle(flow_name: str, ancestor_flows: set[str]) -> None:
    if flow_name in ancestor_flows:
        logger.warning(
            "Possible subflow cycle: '%s' already in ancestry: %s",
            flow_name,
            ", ".join(sorted(ancestor_flows)),
        )
