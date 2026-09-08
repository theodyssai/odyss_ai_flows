"""Verify the shared LLM connection resolver (`resolve_llm_connection`).

Builds a ConfigManager in-process and toggles `node_scope` to exercise the
registry shape (`llm_config` + `llm_connection_name`), the scalar overlay, and
the legacy `oai_connection_name` fallback. No live LLM calls, no plugins.
"""

from __future__ import annotations

from pathlib import Path

from odyss_ai_flows.core.config.context import _config_context, node_scope
from odyss_ai_flows.core.config.manager import ConfigManager
from odyss_ai_flows.core.config.tree import ConfigNode
from odyss_ai_flows.core.handlers.llm import resolve_llm_connection


def _node(name: str, parent: ConfigNode, config: dict) -> ConfigNode:
    child = ConfigNode(name=name, path=parent.path / name, parent=parent)
    child.config = config
    parent.children[name] = child
    return child


async def run_scenario():
    root = ConfigNode(name="", path=Path("/"))
    root.config = {}

    registry = _node("registry", root, {
        "llm_connection_name": "azure_main",
        "llm_config": {
            "azure_main": {"endpoint": "A", "api_version": "v1"},
            "gpt4_eu":    {"endpoint": "B", "api_version": "v2"},
        },
    })
    _node("inner", registry, {
        "llm_connection_name": "gpt4_eu",
        "llm_config": {"temperature": 0.2},
    })
    _node("legacy", root, {
        "oai_connection_name": "legacy_conn",
        "legacy_conn": {"endpoint": "L", "api_version": "vL"},
    })
    _node("legacy_selector", root, {
        "oai_connection_name": "gpt4_eu",
        "llm_config": {
            "azure_main": {"endpoint": "A", "api_version": "v1"},
            "gpt4_eu":    {"endpoint": "B", "api_version": "v2"},
        },
    })
    _node("single", root, {
        "llm_config": {"only": {"endpoint": "S", "api_version": "vS"}},
    })
    _node("ambiguous", root, {
        "llm_config": {"a": {"endpoint": "Pa"}, "b": {"endpoint": "Pb"}},
    })

    mgr = ConfigManager(root)
    cfg_token = _config_context.set(mgr)

    async def at(scope: str):
        tok = node_scope.set(scope)
        try:
            return await resolve_llm_connection(legacy_default="unused")
        finally:
            node_scope.reset(tok)

    try:
        # Selector picks the active profile.
        cfg = await at("registry")
        assert cfg == {"endpoint": "A", "api_version": "v1"}, cfg

        # Nested scope overrides the selector; the deep-merged scalar overlay
        # patches the chosen profile without naming it.
        cfg = await at("registry/inner")
        assert cfg == {
            "endpoint": "B", "api_version": "v2", "temperature": 0.2,
        }, cfg

        # Single-entry registry resolves with no selector.
        cfg = await at("single")
        assert cfg == {"endpoint": "S", "api_version": "vS"}, cfg

        # Legacy bare shape: oai_connection_name selects a top-level dict.
        cfg = await at("legacy")
        assert cfg == {"endpoint": "L", "api_version": "vL"}, cfg

        # Legacy selector inside the registry: oai_connection_name picks a
        # profile when llm_connection_name is unset.
        cfg = await at("legacy_selector")
        assert cfg == {"endpoint": "B", "api_version": "v2"}, cfg

        # Ambiguous registry, no selector -> RuntimeError listing the names.
        raised = False
        tok = node_scope.set("ambiguous")
        try:
            await resolve_llm_connection(legacy_default="unused")
        except RuntimeError as e:
            msg = str(e)
            raised = "a" in msg and "b" in msg and "llm_connection_name" in msg
        finally:
            node_scope.reset(tok)
        assert raised, "expected RuntimeError on ambiguous registry"

        # Unknown selector -> KeyError listing the visible profiles.
        mgr.override("registry", "llm_connection_name", "ghost")
        raised = False
        tok = node_scope.set("registry")
        try:
            await resolve_llm_connection(legacy_default="unused")
        except KeyError as e:
            msg = str(e)
            raised = (
                "ghost" in msg
                and "azure_main" in msg
                and "gpt4_eu" in msg
            )
        finally:
            node_scope.reset(tok)
        assert raised, "expected KeyError on unknown selector"

    finally:
        _config_context.reset(cfg_token)

    return {"ok": True}
