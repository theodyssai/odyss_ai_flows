# Copyright 2026 ODYSS.AI AG
# SPDX-License-Identifier: Apache-2.0
#
# See the NOTICE file for attribution information.
import ast
import inspect
import re
from pathlib import Path
from typing import Optional

import networkx as nx

from odyss_ai_flows.core.builder.types import FlowStructure, FlowNode


_NGET_JINJA2_RE = re.compile(r"""nget\(\s*['"]([^'"]+)['"]\s*\)""")


# ---------------------------------------------------------
# Source extraction
# ---------------------------------------------------------

class _NgetVisitor(ast.NodeVisitor):
    def __init__(self):
        self.deps: list[str] = []

    def visit_Call(self, node: ast.Call):
        func = node.func
        is_nget = (
            (isinstance(func, ast.Name) and func.id == "nget")
            or (isinstance(func, ast.Attribute) and func.attr == "nget")
        )
        if (
            is_nget
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            self.deps.append(node.args[0].value)
        self.generic_visit(node)


def extract_nget_deps(source: str) -> list[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    visitor = _NgetVisitor()
    visitor.visit(tree)
    return visitor.deps


# ---------------------------------------------------------
# Filesystem-based graph builder
# ---------------------------------------------------------

def build_flow_graph(flow_path: Path) -> nx.DiGraph:
    graph: nx.DiGraph = nx.DiGraph()

    for py_file in sorted(flow_path.glob("*.py")):
        if py_file.name == "__init__.py":
            continue

        node_name = py_file.stem
        graph.add_node(node_name)

        try:
            source = py_file.read_text(encoding="utf-8")
        except OSError:
            continue

        for dep in extract_nget_deps(source):
            graph.add_edge(node_name, dep)

    for jinja_file in sorted(flow_path.glob("*.jinja2")):
        node_name = jinja_file.stem
        graph.add_node(node_name)

        try:
            source = jinja_file.read_text(encoding="utf-8")
        except OSError:
            continue

        for dep in _NGET_JINJA2_RE.findall(source):
            graph.add_edge(node_name, dep)

    return graph


# ---------------------------------------------------------
# FlowStructure-based graph builder (handles virtual nodes)
# ---------------------------------------------------------

def _get_node_source(node: FlowNode) -> Optional[str]:
    if node.content:
        return node.content

    if node.path:
        try:
            return node.path.read_text(encoding="utf-8")
        except OSError:
            return None

    if node.callable_obj is not None:
        try:
            return inspect.getsource(node.callable_obj)
        except (OSError, TypeError):
            return None

    return None


def build_graph_from_structure(structure: FlowStructure) -> nx.DiGraph:
    graph: nx.DiGraph = nx.DiGraph()
    known_nodes = set(structure.nodes)

    for name, node in structure.nodes.items():
        graph.add_node(name)

        if node.kind != "python":
            continue

        source = _get_node_source(node)
        if source is None:
            continue

        for dep in extract_nget_deps(source):
            if dep in known_nodes:
                graph.add_edge(name, dep)

    return graph
