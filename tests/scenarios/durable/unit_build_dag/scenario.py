from __future__ import annotations

from pathlib import Path

from odyss_ai_flows_durable._contracts.cycle_detection import assert_dag_acyclic
from odyss_ai_flows_durable._contracts.dag import build_dag
from odyss_ai_flows_durable._contracts.exceptions import OrchestrationError

_FIXTURES = Path(__file__).parent / "fixtures"


async def run_scenario() -> None:
    # build_dag now returns a networkx DiGraph (via core's build_flow_graph); an edge points
    # from a node to each of its string-literal nget dependencies. A node's upstream deps are
    # its successors; its downstream dependents are its predecessors.
    mixed = build_dag(str(_FIXTURES / "mixed"))

    # __init__.py is skipped; the .jinja2 node is discovered alongside the .py nodes.
    assert set(mixed.nodes) == {
        "producer", "consumer_literal", "consumer_var", "consumer_fnref", "report",
    }, set(mixed.nodes)

    # Only the string-literal nget form produces an edge. A variable or a function reference
    # is silently dropped — the durable DAG loses the edge (§4.6).
    assert set(mixed.successors("consumer_literal")) == {"producer"}
    assert set(mixed.successors("consumer_var")) == set()
    assert set(mixed.successors("consumer_fnref")) == set()
    assert set(mixed.successors("report")) == {"producer"}   # .jinja2 regex edge
    assert set(mixed.successors("producer")) == set()
    # predecessors invert the edges (the node's downstream dependents).
    assert set(mixed.predecessors("producer")) == {"consumer_literal", "report"}

    diamond = build_dag(str(_FIXTURES / "diamond"))
    assert sorted(diamond.nodes) == ["a", "b", "c", "d"], sorted(diamond.nodes)
    assert set(diamond.predecessors("a")) == {"b", "c"}      # a feeds b and c
    assert set(diamond.successors("d")) == {"b", "c"}        # d depends on b and c

    # A nonexistent flow dir yields an empty graph, not an error.
    empty = build_dag(str(_FIXTURES / "does_not_exist"))
    assert empty.number_of_nodes() == 0 and empty.number_of_edges() == 0

    # Cycle detection (PR 69): assert_dag_acyclic is silent on acyclic DAGs and raises
    # OrchestrationError naming the cycle path on a cyclic one. This is what
    # DurableFunctionsExecutor.start() runs before dispatching an orchestration.
    assert_dag_acyclic(mixed, "mixed")        # acyclic -> no raise
    assert_dag_acyclic(diamond, "diamond")    # acyclic -> no raise

    cycle = build_dag(str(_FIXTURES / "cycle"))
    assert set(cycle.successors("node_a")) == {"node_b"}
    assert set(cycle.successors("node_b")) == {"node_a"}
    try:
        assert_dag_acyclic(cycle, "cycle")
        raise AssertionError("expected OrchestrationError for a cyclic DAG")
    except OrchestrationError as exc:
        assert "cycle" in str(exc).lower(), str(exc)
        assert "node_a" in str(exc) and "node_b" in str(exc), str(exc)
