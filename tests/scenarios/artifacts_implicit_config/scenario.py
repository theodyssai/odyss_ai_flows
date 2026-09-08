from __future__ import annotations

import asyncio

from odyss_ai_flows_artifacts import (
    ArtifactManager,
    close_all_shared_backends,
    register_backend,
)
from odyss_ai_flows_artifacts.artifact_manager import _shared_backends
from odyss_ai_flows_artifacts.backends.azure_sql import AzureSQLBackend

from tests.artifact_helpers import InMemoryBackend


class CountingInMemoryBackend(InMemoryBackend):
    construct_count = 0
    close_count = 0

    def __init__(self):
        super().__init__()
        type(self).construct_count += 1

    async def close(self) -> None:
        type(self).close_count += 1
        await super().close()


async def run_scenario():
    register_backend("counting_inmem", CountingInMemoryBackend)

    # Start clean — earlier scenarios in the suite must not have left state.
    await close_all_shared_backends()
    CountingInMemoryBackend.construct_count = 0
    CountingInMemoryBackend.close_count = 0

    # 1. Implicit init — two ArtifactManager() calls share the backend.
    am1 = ArtifactManager()
    am2 = ArtifactManager()

    # Initialisation is lazy — no backend yet, no construction happened.
    assert am1.backend is None
    assert am2.backend is None
    assert CountingInMemoryBackend.construct_count == 0

    # First awaited call triggers resolution; cget falls back to
    # global_config.json in CWD (set up by global_config.meta.json).
    await am1.create_artifact(alias="from_am1")
    await am1.commit()

    assert am1.backend is not None
    assert isinstance(am1.backend, CountingInMemoryBackend)
    assert CountingInMemoryBackend.construct_count == 1

    # Second manager resolves to the same cached backend.
    await am2.create_artifact(alias="from_am2")
    await am2.commit()
    assert am2.backend is am1.backend
    assert CountingInMemoryBackend.construct_count == 1
    assert "shared_inmem" in _shared_backends

    # Both artifacts visible through either manager (they share state).
    rows = await am1.query_artifacts()
    aliases = sorted(r.alias for r in rows)
    assert aliases == ["from_am1", "from_am2"]

    # 2. Explicit backend bypasses the cache; from_config owns its backend.
    explicit = ArtifactManager(backend=InMemoryBackend())
    assert explicit.backend is not am1.backend
    assert explicit._owns_backend is False
    owned = ArtifactManager.from_config({
        "backend": "counting_inmem",
        "backend_args": {},
    })
    assert owned.backend is not am1.backend
    assert owned._owns_backend is True
    assert CountingInMemoryBackend.construct_count == 2  # +1 for from_config

    # 3. schema= goes through Backend.with_schema(). For an explicit
    # backend it's applied eagerly in __init__; for the implicit path
    # it's applied during resolution.
    eager = ArtifactManager(schema="eager", backend=AzureSQLBackend(dsn="i", schema="base"))
    assert eager.backend._schema == "eager"
    assert eager.backend._owns_pools is False  # view, not the original

    am_schema_a = ArtifactManager(schema="A")
    await am_schema_a.create_artifact(alias="schema_a")
    await am_schema_a.commit()
    # InMemoryBackend.with_schema falls through to the protocol default
    # (returns self), so the backend is identical to am1's.
    assert am_schema_a.backend is am1.backend
    assert CountingInMemoryBackend.construct_count == 2  # no new construct

    # Real check for AzureSQLBackend — views share pool wrappers but are
    # distinct objects, and close() on the view is a no-op.
    base_sql = AzureSQLBackend(dsn="ignored", schema="base")
    view_x = base_sql.with_schema("x")
    view_y = base_sql.with_schema("y")
    assert view_x is not base_sql
    assert view_y is not base_sql
    assert view_x is not view_y
    assert view_x._auto is base_sql._auto
    assert view_y._auto is base_sql._auto
    assert view_x._tx is base_sql._tx
    assert view_x._schema == "x"
    assert view_y._schema == "y"
    assert view_x._owns_pools is False
    assert base_sql._owns_pools is True
    assert base_sql.with_schema("base") is base_sql  # identity for same schema
    # Closing the view does not close the shared pools (no-op).
    await view_x.close()

    # 4. Concurrent construction — the init lock prevents double-build.
    await close_all_shared_backends()
    CountingInMemoryBackend.construct_count = 0
    CountingInMemoryBackend.close_count = 0

    async def hammer():
        am = ArtifactManager()
        await am.create_artifact(alias="hammer")
        return am

    managers = await asyncio.gather(*(hammer() for _ in range(10)))
    assert CountingInMemoryBackend.construct_count == 1
    hammer_backend = managers[0].backend
    for m in managers[1:]:
        assert m.backend is hammer_backend

    # 5. close_all_shared_backends clears the cache and closes each backend.
    # Existing managers keep their now-closed backend reference — using them
    # is the caller's bug. A fresh manager re-resolves cleanly.
    await close_all_shared_backends()
    assert _shared_backends == {}
    assert CountingInMemoryBackend.close_count == 1

    am_fresh = ArtifactManager()
    await am_fresh.create_artifact(alias="after_close")
    await am_fresh.commit()
    assert CountingInMemoryBackend.construct_count == 2
    assert am_fresh.backend is not hammer_backend

    # 6. backend_args in the flat config is rejected with a clear error.
    await close_all_shared_backends()
    from odyss_ai_flows_artifacts import artifact_manager as am_mod

    async def bad_config():
        return ("x", {"backend": "counting_inmem", "backend_args": {}})

    real_lookup = am_mod._resolve_artifact_config
    am_mod._resolve_artifact_config = bad_config
    try:
        am_bad_args = ArtifactManager()
        raised = False
        try:
            await am_bad_args.create_artifact(alias="should_fail")
        except ValueError as e:
            raised = "backend_args" in str(e)
        assert raised, "expected ValueError mentioning backend_args"
    finally:
        am_mod._resolve_artifact_config = real_lookup

    # 7. Missing config → explicit error.
    await close_all_shared_backends()

    async def empty_lookup():
        return None

    am_mod._resolve_artifact_config = empty_lookup
    try:
        am_bad = ArtifactManager()
        try:
            await am_bad.create_artifact(alias="should_fail")
        except RuntimeError as e:
            assert "artifact_config" in str(e)
        else:
            raise AssertionError("expected RuntimeError on missing config")
    finally:
        am_mod._resolve_artifact_config = real_lookup

    # 8. Resolver-level behaviours — exercise _resolve_artifact_config
    #    directly by stubbing cget on the odyss_ai_flows module surface.
    import odyss_ai_flows

    real_cget = odyss_ai_flows.cget

    def _stub_cget(registry, selector):
        async def fake_cget(key, default=None, *, scope=None):
            if key == "artifact_config":
                return registry
            if key == "am_name":
                return selector
            return default
        return fake_cget

    # 8a. Legacy flat shape — backwards compat. The whole `artifact_config`
    #     block is treated as one pool entry; its `am_name` field becomes
    #     the cache key. The sibling `am_name` selector is ignored in this
    #     mode (the flat block is self-contained).
    odyss_ai_flows.cget = _stub_cget(
        {"am_name": "legacy_pool",
         "backend": "counting_inmem",
         "dsn": "ignored"},
        None,
    )
    try:
        resolved = await am_mod._resolve_artifact_config()
        assert resolved == (
            "legacy_pool",
            {"backend": "counting_inmem", "dsn": "ignored"},
        ), f"unexpected legacy translation: {resolved}"
    finally:
        odyss_ai_flows.cget = real_cget

    # 8a'. Legacy flat shape missing `am_name` → TypeError with migration hint.
    odyss_ai_flows.cget = _stub_cget(
        {"backend": "counting_inmem", "dsn": "ignored"}, None,
    )
    try:
        try:
            await am_mod._resolve_artifact_config()
        except TypeError as e:
            msg = str(e)
            assert "am_name" in msg and "registry" in msg, (
                f"expected migration hint, got: {e}"
            )
        else:
            raise AssertionError(
                "expected TypeError on flat shape missing am_name"
            )
    finally:
        odyss_ai_flows.cget = real_cget

    # 8b. Unknown-selector KeyError lists available names.
    odyss_ai_flows.cget = _stub_cget(
        {"openai_test": {"backend": "counting_inmem"},
         "prod": {"backend": "counting_inmem"}},
        "ghost",
    )
    try:
        try:
            await am_mod._resolve_artifact_config()
        except KeyError as e:
            msg = str(e)
            assert "ghost" in msg and "openai_test" in msg and "prod" in msg
        else:
            raise AssertionError("expected KeyError on unknown selector")
    finally:
        odyss_ai_flows.cget = real_cget

    # 8c. Single-entry auto-resolve is silent (no selector needed).
    odyss_ai_flows.cget = _stub_cget(
        {"only": {"backend": "counting_inmem"}}, None,
    )
    try:
        resolved = await am_mod._resolve_artifact_config()
        assert resolved == ("only", {"backend": "counting_inmem"})
    finally:
        odyss_ai_flows.cget = real_cget

    # 8d. Multi-entry without selector → RuntimeError listing all names.
    odyss_ai_flows.cget = _stub_cget(
        {"openai_test": {"backend": "counting_inmem"},
         "prod": {"backend": "counting_inmem"}},
        None,
    )
    try:
        try:
            await am_mod._resolve_artifact_config()
        except RuntimeError as e:
            msg = str(e)
            assert "openai_test" in msg and "prod" in msg and "am_name" in msg
        else:
            raise AssertionError("expected RuntimeError on ambiguous registry")
    finally:
        odyss_ai_flows.cget = real_cget

    return {"ok": True}
