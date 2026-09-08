"""Verify that the named-keys `artifact_config` registry composes along the
scope chain: ancestor pools remain reachable from nested scopes, deeper
scopes can extend the registry with new pools, and the sibling `am_name`
selector picks the active pool per scope.

The scenario does not depend on filesystem-driven config — it builds a
small ConfigManager in-process and toggles `node_scope` to exercise the
resolver paths directly.
"""

from __future__ import annotations

from pathlib import Path

from odyss_ai_flows_artifacts import (
    ArtifactManager,
    close_all_shared_backends,
    register_backend,
)
from odyss_ai_flows_artifacts.artifact_manager import _shared_backends

from odyss_ai_flows.core.config.context import _config_context, node_scope
from odyss_ai_flows.core.config.manager import ConfigManager
from odyss_ai_flows.core.config.tree import ConfigNode

from tests.artifact_helpers import InMemoryBackend


async def run_scenario():
    register_backend("inmem", InMemoryBackend)

    # Build the tree directly. The registry layers add new entries at the
    # nested scope; the scalar selector `am_name` overrides on the leaf.
    #
    #   /         am_name=openai_test
    #             artifact_config={openai_test, prod}
    #   /nested   am_name=prod   (overrides selector for the nested scope)
    #             artifact_config={override}  (deep-merged into the parent's
    #                                          registry → all three visible)
    root = ConfigNode(name="", path=Path("/"))
    root.config = {
        "am_name": "openai_test",
        "artifact_config": {
            "openai_test": {"backend": "inmem"},
            "prod":        {"backend": "inmem"},
        },
    }
    nested = ConfigNode(name="nested", path=Path("/nested"), parent=root)
    nested.config = {
        "am_name": "prod",
        "artifact_config": {
            "override": {"backend": "inmem"},
        },
    }
    root.children["nested"] = nested

    mgr = ConfigManager(root)
    cfg_token = _config_context.set(mgr)

    await close_all_shared_backends()

    try:
        # 1. Root scope binds to the selector's pool (openai_test).
        root_token = node_scope.set("")
        try:
            am_root = ArtifactManager()
            await am_root.create_artifact(alias="r1")
            await am_root.commit()
            assert am_root.backend is not None
            assert "openai_test" in _shared_backends
            backend_openai = _shared_backends["openai_test"][0]
            assert am_root.backend is backend_openai
        finally:
            node_scope.reset(root_token)

        # 2. Nested scope overrides the selector → picks `prod`. The pool was
        #    defined at the root scope and is reachable from here without
        #    redefinition. Distinct backend from the root manager.
        nested_token = node_scope.set("nested")
        try:
            am_nested = ArtifactManager()
            await am_nested.create_artifact(alias="n1")
            await am_nested.commit()
            assert "prod" in _shared_backends
            backend_prod = _shared_backends["prod"][0]
            assert am_nested.backend is backend_prod
            assert am_nested.backend is not am_root.backend

            # 3. Override the selector to the nested-only pool. The registry
            #    dict-merges across scopes, so `override` is selectable from
            #    here. Mutating mgr.override flips `am_name` for the same
            #    scope without rebuilding the tree.
            mgr.override("nested", "am_name", "override")
            am_override = ArtifactManager()
            await am_override.create_artifact(alias="o1")
            await am_override.commit()
            assert "override" in _shared_backends
            backend_override = _shared_backends["override"][0]
            assert am_override.backend is backend_override
            assert am_override.backend is not am_root.backend
            assert am_override.backend is not am_nested.backend
        finally:
            node_scope.reset(nested_token)

        # 4. From the root scope, the nested-only pool is invisible — its
        #    registry entry only exists in the nested layer. Asking for it
        #    raises KeyError listing the pools that ARE visible at root.
        root_token = node_scope.set("")
        try:
            mgr.override("", "am_name", "override")
            am_bad = ArtifactManager()
            raised = False
            try:
                await am_bad.create_artifact(alias="bad")
            except KeyError as e:
                msg = str(e)
                raised = (
                    "override" in msg
                    and "openai_test" in msg
                    and "prod" in msg
                )
            assert raised, (
                "expected KeyError listing root-visible pools when selecting "
                "a nested-only pool from root scope"
            )
        finally:
            node_scope.reset(root_token)

        # 5. All three pools are cached and distinct objects.
        assert {"openai_test", "prod", "override"}.issubset(
            _shared_backends.keys()
        )
        b_open = _shared_backends["openai_test"][0]
        b_prod = _shared_backends["prod"][0]
        b_over = _shared_backends["override"][0]
        assert b_open is not b_prod
        assert b_prod is not b_over
        assert b_open is not b_over

    finally:
        await close_all_shared_backends()
        _config_context.reset(cfg_token)

    return {"ok": True}
