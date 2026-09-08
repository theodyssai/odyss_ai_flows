# odyss_ai_flows_artifacts

Artifact storage and lifecycle management for `odyss_ai_flows`. Refactor of the legacy `old_flows/artifacts` system into a focused, batch-oriented plugin with a pluggable backend layer.

---

## Table of contents

- [Installation](#installation)
- [Quick start](#quick-start)
- [Core concepts](#core-concepts)
- [Implicit config](#implicit-config)
- [Public API](#public-api)
- [Backends](#backends)
- [Adapters](#adapters)
- [Testing](#testing)
- [Migration from `old_flows/artifacts`](#migration-from-old_flowsartifacts)
- [Architectural changes](#architectural-changes)

---

## Installation

```bash
cd odyss_ai
pip install -e plugins/odyss_ai_flows_artifacts
```

The plugin depends on `aioodbc` for the default Azure SQL backend. Custom backends can avoid that dependency.

## Quick start

### Default — implicit, config-driven (recommended)

Put an `artifact_config` registry plus a sibling `am_name` selector in `global_config.json` (or any closer flow/node `config.json` — see [Implicit config](#implicit-config) below):

```jsonc
{
  "am_name": "main",
  "artifact_config": {
    "main": {
      "dsn": "DRIVER={...};...",
      "adapters_path": "adapters"
    }
  }
}
```

The registry is keyed by pool name; the scalar `am_name` picks which entry is active for the current scope. A nested flow scope can switch pools by overriding `am_name`, or add new pools by extending the registry — `cget` deep-merges the registry along the scope chain and resolves the selector with closest-scope-wins.

Then anywhere in a flow node (or a standalone script run from the project root):

```python
from odyss_ai_flows_artifacts import ArtifactManager, REL_SUMMARY_OF

async def handler():
    manager = ArtifactManager()                # reads artifact_config via cget
    doc = await manager.create_artifact(alias="doc-1", tags=["raw"])
    await doc.set_metadata("score", 0.91)
    await doc.add_journal_entry("ingested", entry_type="lifecycle")

    summary = await manager.create_artifact(alias="doc-1-summary")
    await manager.add_relationship(
        summary.id, doc.id, REL_SUMMARY_OF,
        metadata={"confidence": 0.82, "method": "tfidf"},
    )

    token = await manager.commit()             # single backend round-trip
```

Two `ArtifactManager()` calls resolved under the same `am_name` share **one backend** (one connection pool). Selecting a different `am_name` — either a different default in `global_config.json` or a per-scope override in a closer `config.json` — gives you an isolated pool. See [Implicit config](#implicit-config).

### Explicit backend (escape hatch)

```python
from odyss_ai_flows_artifacts import ArtifactManager
from odyss_ai_flows_artifacts.backends.azure_sql import AzureSQLBackend

backend = AzureSQLBackend(dsn="DRIVER={...};...", schema="myschema")
await backend.init_schema()

manager = ArtifactManager(backend=backend)     # bypasses the shared cache
```

Use this when you need a backend the implicit path can't produce (a test double, a one-off DSN, a backend you want to own and close yourself).

### One-call form

```python
manager = ArtifactManager.from_config({
    "backend": "azure_sql",
    "backend_args": {"dsn": "...", "schema": "myschema"},
    "adapters_path": "/path/to/adapters",
})
```

Constructs its own backend and **owns** it (closed by `await manager.aclose()`). Does not participate in the shared cache.

## Core concepts

- **`Artifact`** — value object. Holds row data (`id`, `alias`, `adapter_name`, `uri`, `origin_operation_id`, `tags`, `is_deleted`) and in-memory `metadata: dict[str, MetadataValue]`. Mutations stage through the manager.
- **`ArtifactRelationship`** — directed named edge `(from_id, to_id, relationship_type, metadata?)`. Reads as a sentence: `from_id {relationship_type} to_id` (e.g. `child derived_from parent`). Replaces the parent/child/derivative-only model.
- **`MetadataValue`** — `Union[str, int, float, bool, None]`. Validated synchronously at the boundary; round-trips through backends with a type tag.
- **`ArtifactManager`** — orchestration: staging (unit-of-work), identity-map cache, batch query planning. No SQL knowledge.
- **`Backend`** — Protocol the manager talks to. Owns SQL/schema/indexes/batching. `AzureSQLBackend` ships default and self-registers under `"azure_sql"`.
- **`AdapterRegistry`** — per-manager discovery & loading of adapter modules (filesystem + built-in + programmatic).

### Staging vs committed vs deleted

| State | Meaning | Visibility |
|---|---|---|
| **committed** | Lives in backend. | Always queryable. |
| **staged** | Pending edit held by manager. | Visible to queries with `include_staged=True` (default). Flushed atomically by `commit()`. |
| **dirty** | An artifact with at least one staged edit. | `artifact.dirty` returns `True`. |
| **soft-deleted** | Backend row has `is_deleted=1`. | Hidden unless `include_deleted=True`. Reversible via `restore_artifact`. |
| **hard-deleted** | Backend row + cascade (relationships, metadata, journal) removed. | Irreversible. |

Deletes (both kinds) are **immediate** — not part of staging or `commit()`. They execute against the backend the moment they're called and are not undone by `rollback()`. Edits go through staging; deletes don't.

## Implicit config

`ArtifactManager()` resolves its backend lazily on the first awaited call. The resolver reads two layers via `cget`:

- **`artifact_config`** — a registry keyed by pool name. Dict-merges along the scope chain so ancestor pools stay visible at deeper scopes; deeper scopes can deep-merge fields per pool or add new entries.
- **`am_name`** — a sibling scalar selector. Resolved with closest-scope-wins.

Both layers use standard `cget` precedence (root → ancestor folders → flow folder → node), so a closer `config.json` always wins.

### Config shape

```jsonc
{
  "am_name": "main",                              // selects which pool is active
  "artifact_config": {
    "main": {
      "backend": "azure_sql",                     // optional, default "azure_sql"
      "dsn": "DRIVER={...};...",                  // forwarded to backend (flat kwargs)
      "min_pool_size": 3,
      "max_pool_size": 5,
      "extra_indexes": [],
      "adapters_path": "adapters",                // used to build AdapterRegistry
      "adapter_mapping": {}
    },
    "analytics": {
      "dsn": "DRIVER={...};...",
      "max_pool_size": 20
    }
  }
}
```

Inside a per-pool entry, anything not in `{backend, adapters_path, adapter_mapping}` is forwarded as a kwarg to the backend factory. `backend_args` is **not** accepted here — that form belongs to `ArtifactManager.from_config(...)`. Mixing them raises `ValueError`.

### Selecting a pool

| Situation | Behaviour |
|---|---|
| `am_name` set + name present in registry | That entry is used. |
| `am_name` set + name absent | `KeyError` listing the pools that are visible at the current scope. |
| `am_name` unset + registry has 1 entry | The lone entry is used silently. |
| `am_name` unset + registry has >1 entries | `RuntimeError` listing the available names — set `am_name` in scope to disambiguate. There is no insertion-order fallback. |
| Legacy flat shape (see below) | Translated to a single-pool registry entry transparently. |

### Scalar overlays — patch the active pool without naming it

Inside `artifact_config`, **dict** values are pools and **scalar** (non-dict)
values are *overlays*: each scalar is merged onto whichever pool `am_name`
selects. So a nested scope overrides a single field of the **active** pool by
writing just that field — no pool name, no redeclare:

```jsonc
// global_config.json — the pools
{
  "am_name": "main",
  "artifact_config": {
    "main": { "dsn": "DRIVER={...};...", "adapters_path": "adapters" }
  }
}

// some_flow/config.json — swap adapters for this scope, no pool name needed
{ "artifact_config": { "adapters_path": "special/adapters" } }
```

The overlay key is the literal pool field (`adapters_path`, `max_pool_size`, …).
`cget` deep-merges `artifact_config` along the scope chain, so the ancestor's
pools and the nested scope's scalar overlay arrive together; the resolver picks
the pool and merges the scalars on top. Consequences:

- **Scalar-only.** A pool field whose value is itself a dict (only
  `adapter_mapping` today) can't be overlaid this way — a dict reads as a pool.
  Override those with the named-pool form `{"artifact_config": {"main": {...}}}`.
- **What actually takes effect:** the connection pool stays shared by `am_name`,
  and only the cheap, connectionless `AdapterRegistry` is rebuilt per scope from
  the resolved config. So `adapters_path` / `adapter_mapping` overlays apply
  per-scope even when another scope resolved the same pool first. An overlay of
  a *backend* field (e.g. `dsn`, `max_pool_size`) only bites on the **first**
  resolution under that `am_name`, because the backend is cached by `am_name`;
  reliably varying a backend field per scope means giving it a distinct
  `am_name`.

### Backwards compatibility — legacy single-pool flat shape

The pre-registry shape still works. If `artifact_config` carries its own `am_name` **field inside the block**, the whole block is treated as one pool entry and that field becomes the cache key. The sibling `am_name` selector is not consulted in this mode — a flat block is self-contained.

```jsonc
// Legacy — still supported, single pool only.
{
  "artifact_config": {
    "am_name": "main",
    "backend": "azure_sql",
    "dsn": "DRIVER={...};..."
  }
}
```

A flat block missing `am_name` raises `TypeError` with a migration hint. The registry form is recommended for any new config — it composes additively across scopes and supports multiple pools.

Shape detection: `artifact_config` is treated as the **legacy flat shape** iff it carries a top-level `am_name` field; otherwise it's a **registry** — dict values are pools, scalar values are overlays (see [Scalar overlays](#scalar-overlays--patch-the-active-pool-without-naming-it)). This is what lets scalar overlays coexist with pools without being mistaken for a flat block.

### Pool sharing

The plugin holds a process-wide `_shared_backends` dict keyed by `am_name`. Two managers resolved under the same `am_name` get the **same backend object** — same connection pool. Switching `am_name` builds (or reuses) a different pool.

```python
am_a = ArtifactManager()           # am_name="main" → backend B1
am_b = ArtifactManager()           # am_name="main" → reuses B1
assert am_a.backend is am_b.backend
```

A node-level override gives an isolated pool without code changes — either switch the selector or define a new pool inline:

```jsonc
// some_flow/some_node.config.json — switch to a pool defined in the ancestor
{ "am_name": "analytics" }

// some_other_flow/config.json — add a brand-new pool and select it
{
  "am_name": "isolated_pool",
  "artifact_config": {
    "isolated_pool": { "dsn": "DRIVER={...};...", "max_pool_size": 20 }
  }
}
```

### Schemas share the pool

`schema=` is an `__init__` argument, **not** a config key. It goes through `Backend.with_schema(schema)` — for `AzureSQLBackend` that returns a lightweight view sharing the same pool wrappers but scoped to a different schema:

```python
am_a = ArtifactManager(schema="tenant_a")
am_b = ArtifactManager(schema="tenant_b")
# Two distinct backend views, ONE underlying connection pool.
```

For an explicit backend, the schema view is applied eagerly in `__init__`:

```python
am = ArtifactManager(schema="tenant_a", backend=base)
# am.backend is already base.with_schema("tenant_a")
```

In-memory and other simple backends inherit the protocol default (`with_schema` returns `self`), which is the right behaviour when the backend doesn't model schemas.

### Standalone (outside a flow)

`cget` falls back to `global_config.json` in the current working directory when no flow context is active, so `ArtifactManager()` works in scripts run from the project root.

### Decoupling

The cget import is lazy and optional — if `odyss_ai_flows` isn't installed, `ArtifactManager()` raises a clear error and the explicit and `from_config` paths still work. The plugin imports nothing else from the flows package.

### Teardown

```python
from odyss_ai_flows_artifacts import close_all_shared_backends

await close_all_shared_backends()   # closes every cached backend, clears the cache
```

Intended for test teardown and process shutdown. Existing managers that already resolved keep their (now-closed) backend reference; constructing a fresh `ArtifactManager()` after the close re-resolves cleanly.

## Public API

Importable from `odyss_ai_flows_artifacts`:

| Symbol | Kind | Purpose |
|---|---|---|
| `ArtifactManager` | class | Main entry point. Construct bare (`ArtifactManager()` / `(schema=...)`) for implicit config-driven init, with `backend=`, or via `ArtifactManager.from_config(dict)`. |
| `close_all_shared_backends` | async function | Close every cached backend and clear the shared cache. Test/shutdown helper. |
| `Artifact` | class | Value object. Constructed via `manager.create_artifact()` / `manager.get_artifact()`. |
| `ArtifactRelationship` | dataclass | `(from_id, to_id, relationship_type, metadata, created_at)`. |
| `REL_DERIVED_FROM` and friends | constants | `REL_SUMMARY_OF`, `REL_CHUNK_OF`, `REL_REFERS_TO`, `REL_EMBEDDING_OF`, `REL_EXPORTED_FROM`. |
| `MetadataValue` | type alias | `Union[str, int, float, bool, None]`. |
| `validate_metadata_value` | function | Raises `TypeError` on unsupported types (lists/dicts/objects/bytes). |
| `serialize_metadata_value` / `deserialize_metadata_value` | functions | Backend round-trip helpers. |
| `Backend` | Protocol | Backend interface. |
| `CommitPayload` | dataclass | What the manager passes to `Backend.commit()`. |
| `ArtifactRow`, `ArtifactFieldUpdate`, `JournalEntry` | dataclasses | Plain data shapes used by backends. |
| `register_backend(name, factory)` | function | Register a backend class under a string name. |
| `get_backend_factory(name)` | function | Look up a registered backend. |
| `AdapterRegistry` | class | Per-manager adapter registry. |
| `register_adapter(name, module_or_callable)` | function | Process-wide adapter registration (for tests / library users). |

### `ArtifactManager` method summary

```python
# Lifecycle
await manager.create_artifact(*, alias=None, adapter_name=None, uri=None, origin_operation_id=None, tags=None)
await manager.create(adapter_name, **kwargs)
await manager.create_<adapter_name>(**kwargs)        # sugar via __getattr__
await manager.get_artifact(id, *, include_staged=True, include_deleted=False)
await manager.get_artifacts(ids, *, include_staged=True, include_deleted=False)
await manager.query_artifact_ids(
    *, alias=None, origin_operation_id=None, adapter_name=None, uri=None,
    tags=None, children_of=None, parents_of=None,
    related=None,         # list[RelFilter]
    journal=None,         # JournalFilter
    include_staged=True, include_deleted=False,
)   # children_of=[p] → artifacts derived from p; parents_of=[c] → c's origins
await manager.query_artifacts(... same kwargs ...)

# Delete (immediate, not staged)
await manager.delete_artifact(id, *, hard=False)
await manager.delete_artifacts(ids, *, hard=False)
await manager.restore_artifact(id)
await manager.restore_artifacts(ids)

# Commit / rollback
token = await manager.commit()            # full atomic commit of staged edits
manager.rollback()                        # discard staged edits (does NOT undo deletes)
await manager.aclose()                    # closes backend iff manager owns it

# Relationships  (edge reads "from_id {relationship_type} to_id")
await manager.add_relationship(from_id, to_id, relationship_type, metadata=None)
await manager.add_relationships([ArtifactRelationship, ...])
await manager.delete_relationship(from_id, to_id, relationship_type)
await manager.query_relationships(*, from_id=None, to_id=None, relationship_type=None, include_staged=True)
await manager.query_outgoing_relationships(from_id, relationship_type=None, *, include_staged=True)
await manager.query_incoming_relationships(to_id, relationship_type=None, *, include_staged=True)
# Convenience wrappers over REL_DERIVED_FROM (child --derived_from--> parent)
await manager.parent_relationships(id)     # outgoing: id's origins
await manager.child_relationships(id)       # incoming: artifacts derived from id

# Metadata
await manager.set_metadata(id, key, value)
await manager.set_metadata_bulk(id, mapping)
await manager.delete_metadata(id, key)
await manager.delete_metadata_bulk(pairs)
await manager.get_metadata_bulk(ids, keys=None, *, include_staged=True)

# Journal
await manager.add_journal_entry(id, content, entry_type=None)
await manager.add_journal_entries([JournalEntry, ...])
await manager.query_journal_entries(*, artifact_id=None, entry_type=None, before=None, after=None, include_staged=True)
```

### `Artifact` method summary

```python
# Adapter delegation (unchanged from old API)
await a.read(...) / a.write(...) / a.delete(...) / a.exists(...)
a.<adapter_method>(...)                    # __getattr__ → adapter.<adapter_method>(a, ...)

# In-memory metadata access
a["foo"]                                   # a.metadata.get("foo")
a.metadata                                 # dict[str, MetadataValue]

# Mutations (all stage through the manager)
await a.set_metadata(key, value)
await a.set_metadata_bulk(mapping)
await a.delete_metadata(key)
await a.add_journal_entry(content, entry_type=None)

# Relationships
await a.add_relationship(target_or_id, relationship_type, metadata=None)
await a.create_derived_artifact(**kwargs)  # creates + REL_DERIVED_FROM link

# Lazy relationship queries (edges)
await a.parent_relationships()             # → list[ArtifactRelationship]
await a.child_relationships()
# …or resolved Artifact objects directly
await a.parent_artifacts()                 # → list[Artifact]
await a.child_artifacts()

# Misc
a.dirty                                    # bool
a.to_dict()                                # serialization
a.is_deleted                               # reflects backend soft-delete flag
```

## Backends

### Default: `AzureSQLBackend`

```python
from odyss_ai_flows_artifacts.backends.azure_sql import AzureSQLBackend

backend = AzureSQLBackend(
    dsn="DRIVER={...};...",
    schema=None,                # optional table prefix (e.g. "tenant_42")
    min_pool_size=3,
    max_pool_size=5,
    extra_indexes=[             # optional, validated
        {"name": "ix_x", "table": "artifacts", "columns": ["alias", "adapter_name"]},
    ],
)
await backend.init_schema()
```

Self-registers under name `"azure_sql"` at import time, so `ArtifactManager.from_config({"backend": "azure_sql", ...})` works out of the box.

`AzureSQLBackend.with_schema(s)` returns a clone that **shares** the autocommit and transactional pool wrappers (`_auto`, `_tx`) but holds its own `_schema`. The clone's `close()` is a no-op — only the original (with `_owns_pools=True`) tears the pools down. This is what makes `ArtifactManager(schema="tenant_a")` and `ArtifactManager(schema="tenant_b")` share a single pool under the same `am_name`.

### Custom backends

Implement the `Backend` protocol (see [backends/base.py](odyss_ai_flows_artifacts/backends/base.py)) and call `register_backend("my_backend", MyBackendClass)` from bootstrap code:

```python
from odyss_ai_flows_artifacts import Backend, register_backend

class MyBackend:                            # duck-typed against the Protocol
    async def init_schema(self): ...
    async def close(self): ...
    # Optional. Default in the Protocol returns self — fine for backends
    # that don't model schemas. Override to return a pool-sharing view.
    def with_schema(self, schema): return self
    async def get_artifacts(self, ids, *, include_deleted=False): ...
    async def query_artifact_ids(self, *, filters, include_deleted=False): ...
    async def query_relationships(self, *, from_id=None, to_id=None, relationship_type=None): ...
    async def get_metadata_bulk(self, artifact_ids, keys=None): ...
    async def query_journal_entries(self, *, artifact_id=None, entry_type=None, before=None, after=None): ...
    async def commit(self, payload) -> str: ...
    async def soft_delete_artifacts(self, ids): ...
    async def hard_delete_artifacts(self, ids): ...
    async def restore_artifacts(self, ids): ...

register_backend("my_backend", MyBackend)
```

Backends own their own SQL/DDL/indexes/batching. The manager treats them as opaque.

## Adapters

Adapters are Python modules with `async def read/write/delete/exists(artifact, ...)` (any subset). The `AdapterRegistry` discovers them three ways, in priority order:

1. **Per-manager programmatic** — `manager.adapter_registry.register("name", module)`.
2. **Global programmatic** — `register_adapter("name", module)`.
3. **Filesystem** — `.py` files under `adapters_path` (passed to `AdapterRegistry`).
4. **Built-in** — `.py` files inside `odyss_ai_flows_artifacts/built_in_adapters/`.

Once registered, an adapter is callable through `manager.create_<adapter_name>(...)` (sugar via `__getattr__`) or the canonical `manager.create(adapter_name="...", ...)`.

## Testing

A pure-Python `InMemoryBackend` lives at `tests/artifact_helpers.py` (not a scenario itself — won't be discovered). Use it in scenarios that need to exercise the artifact system without spinning up SQL:

```python
from tests.artifact_helpers import InMemoryBackend
from odyss_ai_flows_artifacts import ArtifactManager

async def run_scenario():
    backend = InMemoryBackend()
    manager = ArtifactManager(backend=backend)
    a = await manager.create_artifact(alias="x")
    await manager.commit()
    assert backend.commit_calls == 1
    return {"ok": True}
```

Existing scenarios under `tests/scenarios/`:
- `artifacts_basic` — staging, typed metadata, batch ops, rollback
- `artifacts_relationships` — named relations + convenience helpers
- `artifacts_delete_lifecycle` — soft/hard/restore, cascade, immediate semantics
- `artifacts_include_staged` — overlay semantics
- `artifacts_backend_registry` — `register_backend` + `from_config`
- `artifacts_schema_prefix` — `AzureSQLBackend(schema=...)` plumbing
- `artifacts_implicit_config` — implicit init via the `artifact_config` registry, pool sharing by `am_name`, `with_schema` views, concurrent construction, `close_all_shared_backends`, resolver failure modes (bad shape, unknown selector, ambiguity)
- `artifacts_nested_scope_pool_selection` — additive registry composition along the scope chain, ancestor pool reachable from nested scope, nested-only pool invisible at root scope

Run the suite from `odyss_ai/`:

```bash
python -m tests.tests_runtime.main
```

---

## Migration from `old_flows/artifacts`

The new plugin is a clean rewrite. No automatic data migration is provided — the schema differs significantly.

### Construction

| Old | New |
|---|---|
| `ArtifactManager(config_manager=cfg, schema="x")` | `ArtifactManager(schema="x")` — reads `artifact_config` via `cget` (closest-scope-wins). Or `ArtifactManager(backend=AzureSQLBackend(dsn=..., schema="x"))` for full control. |
| Implicit pool sharing via `_shared_dbs[am_name]` | Same idea, cleaner mechanics: `_shared_backends[am_name]` keyed off the config block, double-checked async lock, schemas share the pool via `Backend.with_schema(...)` instead of being baked into separate pools. |
| Required a global `ConfigurationManager` | `cget` reads from the closest `config.json` automatically. Standalone scripts fall back to `global_config.json` in CWD. `ArtifactManager.from_config({...})` is still available for fully programmatic / test setups. |

### Artifact instance API

| Old | New |
|---|---|
| `a.parents: Set[str]` (eagerly loaded) | `await a.parent_relationships() -> list[ArtifactRelationship]` (lazy, typed) or `await a.parent_artifacts() -> list[Artifact]` |
| `a.derivatives: Set[str]` (eagerly loaded) | `await a.child_relationships()` / `await a.child_artifacts()` (lazy, typed) |
| `a.journal: list[dict]` (eagerly loaded) | `await manager.query_journal_entries(artifact_id=a.id, ...)` (filterable) |
| `a.metadata_kv: dict[str, str]` | `a.metadata: dict[str, MetadataValue]` (typed) |
| `await a.load_additional_metadata()` (required after `get_artifact`) | Gone — `get_artifact`/`get_artifacts` include metadata in one batch |
| `await a.set_metadata_kv(k, v)` | `await a.set_metadata(k, v)` — same semantics, now also accepts int/float/bool/None |
| `await a.delete_metadata_kv(k)` (**immediate DB write**) | `await a.delete_metadata(k)` (**staged**) |
| `Artifact.from_metadata(dict, ...)` (static, untyped dict) | `Artifact.from_row(ArtifactRow, ...)` (classmethod, typed dataclass) |
| `a.config_manager` reference | Removed — explicit DI |

### Manager API

| Old | New |
|---|---|
| `await manager.add_relationship(parent_id, child_id)` | `await manager.add_relationship(from_id, to_id, relationship_type, metadata=None)` (edge reads `from_id {type} to_id`) |
| Only parent/child relationships | Arbitrary named directed relations: `REL_DERIVED_FROM`, `REL_SUMMARY_OF`, `REL_CHUNK_OF`, `REL_REFERS_TO`, `REL_EMBEDDING_OF`, `REL_EXPORTED_FROM`, or any custom string |
| No batch ops | `get_artifacts`, `set_metadata_bulk`, `delete_metadata_bulk`, `get_metadata_bulk`, `add_relationships`, `add_journal_entries` |
| `query_artifact_ids(..., child_ids=[...], derived_from_ids=[...], journal_entry_type=...)` | `query_artifact_ids(..., children_of=[...], parents_of=[...], related=[RelFilter(type, to_id=/from_id=)], journal=JournalFilter(entry_type=, before=, after=))`. `children_of=[p]` returns artifacts derived from `p`; `parents_of=[c]` returns `c`'s origins; multi-id is AND-of-many; arbitrary relationship types go through `related`. |
| `delete_artifact(id)` (hard, immediate) | `delete_artifact(id, hard=False)` — soft by default; `hard=True` for full cascade. Both immediate. |
| (none) | `restore_artifact(id)` — reverses soft delete |
| `set_metadata_kv` accepts `str` only | `set_metadata` accepts `str | int | float | bool | None`; validates synchronously |
| Manager held `schema=` arg | `schema=` lives on `AzureSQLBackend(...)` (backend owns SQL) |

### Call-site migration cheatsheet

```python
# OLD
parent_ids = a.parents
for cid in a.derivatives:
    ...
for entry in a.journal:
    ...
await a.set_metadata_kv("score", "0.91")    # had to stringify
await a.delete_metadata_kv("old")           # wrote immediately

# NEW
parents = await a.parent_artifacts()        # resolved Artifact objects
for child in await a.child_artifacts():
    ...
for entry in await manager.query_journal_entries(artifact_id=a.id):
    ...
await a.set_metadata("score", 0.91)         # actual float
await a.delete_metadata("old")              # stages — requires commit()
```

---

## Architectural changes

Summary of every meaningful change against the legacy `old_flows/artifacts` codebase.

### 1. Module split

The old `artifact_manager.py` (533 lines) and `artifact.py` (236 lines) carried mixed responsibilities: staging, identity-map, SQL, schema, adapter discovery/loading, relationship logic, query construction, commit orchestration. The plugin splits these into focused modules:

| Module | Responsibility |
|---|---|
| `artifact.py` | Value object + adapter delegation. No SQL, no backend access. |
| `relationship.py` | `ArtifactRelationship` dataclass + type constants. |
| `metadata.py` | `MetadataValue` type + (de)serialization + validation. |
| `adapter_registry.py` | Adapter discovery, loading, caching. |
| `artifact_manager.py` | Orchestration: staging, identity-map, query merge. No SQL. |
| `backends/base.py` | `Backend` Protocol + `CommitPayload`. |
| `backends/__init__.py` | `register_backend` / `get_backend_factory`. |
| `backends/azure_sql.py` | All SQL, schema DDL, indexes, batching, pool management. Self-registers. |
| `healable_resource.py` | Verbatim copy from old code. Production-critical. |

### 2. Backend decoupling

`ArtifactManager` no longer knows SQL exists. All SQL/DDL/indexes/batching live behind the `Backend` protocol. The manager assembles a `CommitPayload` and hands it to `backend.commit()` in a single round-trip.

**Why:** Per the refactor spec ("Backend ma być ownerem SQL, batching, indexes, schema, migrations"), to enable swappable backends (`InMemoryBackend` for tests, alternate DBs in production), and to make the manager testable without infrastructure.

### 3. Backend registration

- `register_backend(name, factory)` — explicit string-keyed registry, called from bootstrap code.
- Default `AzureSQLBackend` self-registers under `"azure_sql"` at module import time.
- `ArtifactManager.from_config({"backend": "azure_sql", ...})` looks up the factory and constructs.

**Why:** Predictable, explicit (no entry-point magic), works the same in tests and production.

### 4. Pool sharing by `am_name`, restored cleanly

The old `_shared_dbs[am_name]` pattern at [`old_flows/artifacts/artifact_manager.py:16, 50-53`](../../../old_flows/artifacts/artifact_manager.py) solved a real problem — N nodes per flow each minting their own connection pool causes pool explosion against Azure SQL. The pattern returns as `_shared_backends[am_name]`, but with sharper edges fixed:

| Old failure mode | Fix |
|---|---|
| Same `am_name` + different `dsn` → silent pool reuse. | The first per-pool entry resolved under a given `am_name` wins for the lifetime of the process. `am_name` is the *deliberate* cache key — it lives as the sibling scalar selector and as the key into the `artifact_config` registry, no longer a kwarg sibling. A nested `config.json` with a different `am_name` gets its own pool without code changes. |
| Test isolation impossible. | `close_all_shared_backends()` is exposed as an explicit teardown hook. Tests that need isolation call it between scenarios. |
| Multi-tenant impossible without juggling globals. | `Backend.with_schema(s)` returns a pool-sharing view per schema. One pool, N tenant views. See §5. |
| Concurrent first-init could double-construct. | Module-level `asyncio.Lock` + double-checked-locking pattern in `_get_or_create_shared`. Exercised by `artifacts_implicit_config` section 4 (10-way concurrent hammer). |
| `_shared_dbs` was populated as a side effect of `__init__`. | `__init__` stays sync and pure. Resolution is lazy and explicit — first awaited method calls `_ensure_initialized`, which double-checks under the lock and resolves once. |

### 5. `Backend.with_schema(...)` — pool-sharing seam

Old: `ArtifactManager(schema=...)` formatted SQL itself; the manager held the schema string. After the initial refactor, `AzureSQLBackend(schema=...)` baked the schema in at construction — making different schemas need different pools.

New: schema lives on the **manager** again (per-instance `__init__` arg), but the SQL stays on the backend. The bridge is `Backend.with_schema(s)` — a Protocol method whose default returns `self`. `AzureSQLBackend` overrides it to return a lightweight clone that shares `_auto`/`_tx` pool wrappers but holds its own `_schema`. `close()` on the clone is a no-op; only the original tears the pools down.

Result: `ArtifactManager(schema="A")` and `ArtifactManager(schema="B")` under the same `am_name` go through one cached base backend and one pool, with two schema views. Test backends that don't model schemas (`InMemoryBackend`) get the default identity `with_schema` and Just Work.

### 6. Implicit init via the `artifact_config` registry + `am_name` selector

Old constructor took a `ConfigurationManager` provider object and pulled `dsn`/`am_name`/`adapters_path`/`min_pool_size`/etc. via runtime lookups. Hidden dependencies, untestable without the full config system.

New: the manager calls `cget("artifact_config")` and `cget("am_name")` lazily on first awaited method. `cget` already implements closest-scope-wins precedence (root → ancestors → flow → node) — dicts deep-merge, scalars overwrite — which gives the two layers complementary semantics:

- The **`artifact_config`** registry composes additively along the scope chain. An ancestor scope can declare common pools; a nested scope can add new ones or override individual fields per pool without redeclaring.
- The scalar **`am_name`** selector overwrites at the innermost defining scope, so a node-level `config.json` can switch pools without touching the registry:

```jsonc
// some_flow/some_node.config.json — switch which ancestor pool is active here
{ "am_name": "analytics" }
```

`cget` falls back to `global_config.json` in CWD when no flow context is active, so the implicit path works standalone too. The import is lazy and optional — if `odyss_ai_flows` isn't installed the explicit and `from_config` paths still work.

When `am_name` is unset and the registry has more than one entry the resolver raises `RuntimeError` listing the available names — there is no insertion-order fallback. A single-entry registry resolves silently without a selector.

`ArtifactManager.from_config(dict)` is still available as the fully programmatic path (separate dict shape with `backend_args` nesting — kept distinct from `artifact_config`, whose per-pool entries use flat backend kwargs).

### 7. Per-manager `AdapterRegistry`

Old `_known_adapters` was a module-level cache populated by the first manager's `adapters_path`. Subsequent managers with different paths saw stale state — a latent bug.

**Replaced by:** `AdapterRegistry` instances owned by each manager. Built-in adapter scan is still memoized at module level (it's static per process). Programmatic `register_adapter(name, module)` is symmetric with `register_backend` for tests and library users.

### 8. Relationship model: parent/child → arbitrary named directed

Old:
- One table `artifact_parents(parent_id, child_id)`.
- Only the parent/child relationship existed conceptually.
- No metadata on the edge.
- `Artifact.parents` / `Artifact.derivatives` were eagerly-loaded `Set[str]` of IDs.

New:
- `artifact_relationships(from_id, to_id, relationship_type, metadata_json, created_at)`. Edge reads `from_id {relationship_type} to_id` (e.g. `child derived_from parent`).
- Arbitrary string `relationship_type` — built-in constants `REL_DERIVED_FROM`, `REL_SUMMARY_OF`, `REL_CHUNK_OF`, `REL_REFERS_TO`, `REL_EMBEDDING_OF`, `REL_EXPORTED_FROM`; any custom string works.
- Optional metadata dict per edge (e.g. `{"confidence": 0.82, "method": "tfidf"}`), stored as validated JSON with `CHECK (ISJSON(metadata_json) = 1)`.
- `ArtifactRelationship` is a first-class dataclass returned by query methods.
- Convenience wrappers `parent_relationships`/`child_relationships` (edges) and `parent_artifacts`/`child_artifacts` (resolved objects) map to `REL_DERIVED_FROM`.

### 9. Eager hydration → lazy queries

Old `Artifact` was a hydrated aggregate. Every `get_artifact(id)` required calling `await a.load_additional_metadata()` afterward, which fired four extra DB round-trips for journal, parents, derivatives, metadata_kv.

New `Artifact` carries only the row data + `metadata` (which is included in the original `get_artifacts` batch round-trip). Relationships and journal are fetched on demand via manager queries with proper filters. Eliminates N+1 loading; eliminates the "did I forget to hydrate?" footgun.

### 10. Typed metadata

Old: `Dict[str, str]`. Callers had to stringify everything and lost type fidelity on read-back. Setting a value of the wrong type silently corrupted state.

New: `MetadataValue = Union[str, int, float, bool, None]`. Validated synchronously at the staging boundary (raises `TypeError` on lists/dicts/objects/bytes). Round-trips through the backend via a `meta_type` tag column. `int`/`float`/`bool` stay distinct after fetch — `isinstance(a.metadata["count"], int)` returns `True`, not via accidental coercion.

### 11. Staging consistency

Old code had `delete_metadata_kv` execute against the DB immediately, while every other edit staged. Inconsistent and a source of bugs.

New code stages every edit (creates, metadata sets, metadata deletes, relationship adds, relationship deletes, journal entries). `commit()` flushes them as a single atomic `Backend.commit(payload)`. `rollback()` discards staging in memory.

### 12. Delete decoupled from staging

Per user clarification, delete operations are conceptually distinct from edits and execute immediately:

- `delete_artifact(id, hard=False)` → `backend.soft_delete_artifacts([id])` immediately.
- `delete_artifact(id, hard=True)` → `backend.hard_delete_artifacts([id])` immediately (cascades to relationships, metadata, journal in a single backend transaction).
- `restore_artifact(id)` → `backend.restore_artifacts([id])` immediately.
- `rollback()` does **not** undo deletes (they were never staged).
- If a delete fires while edits are staged for the same id, those staged edits are purged and a warning is logged.

### 13. Soft + hard delete

Old: `delete_artifact` was always hard. No way to reverse.

New: `is_deleted` flag + `deleted_at` timestamp column. Default `delete_artifact()` is soft (reversible via `restore_artifact`). `hard=True` is destructive cascade.

### 14. Default indexes

Old schema had no indexes on `artifact_parents` or `artifact_journal` — a performance gap on any non-trivial graph.

New schema ships defaults out of the box:

| Table | Indexes |
|---|---|
| `artifacts` | `alias`, `adapter_name`, `origin_operation_id` (plus `id` PK) |
| `artifact_relationships` | `(from_id, relationship_type)`, `(to_id, relationship_type)` (plus 3-col PK) |
| `artifact_metadata` | `(meta_key, meta_value)` (plus 2-col PK) |
| `artifact_journal` | `(artifact_id, timestamp)`, `(entry_type, timestamp)` |

User-supplied `extra_indexes` are validated against an allowed table/column whitelist before issuing `CREATE INDEX` — no random SQL execution path.

### 15. Batch operations

Old API was scalar everywhere: `get_artifact(id)`, `set_metadata_kv(id, k, v)`, `add_journal_entry(id, content, type)`. The backend had no batch read API; hydrating N artifacts cost 5N round-trips.

New API exposes batch forms at the manager and the backend:

| Concern | Batch API |
|---|---|
| Artifacts | `get_artifacts(ids)`, `query_artifacts(...)`, `delete_artifacts(ids, hard=)`, `restore_artifacts(ids)` |
| Metadata | `set_metadata_bulk`, `delete_metadata_bulk`, `get_metadata_bulk` |
| Relationships | `add_relationships`, `query_relationships`, `query_outgoing_relationships`, `query_incoming_relationships` |
| Journal | `add_journal_entries`, `query_journal_entries` |

Backend batches all commit operations into a single `Backend.commit(payload)` round-trip, executed inside one transaction with `SET XACT_ABORT ON` and chunked at 200 rows per `executemany`.

### 16. `include_staged` query semantics

Every query method on the manager takes `include_staged: bool = True`:

- `True` (default): overlay staged creates/edits/deletes on top of backend results.
- `False`: backend-only view.

Implementation centralized in `_match_filters` (single Python-side predicate that mirrors backend WHERE semantics) and small per-query overlay merges, to avoid drift between SQL and in-memory filtering.

### 17. `commit()` returns a token

Old `commit()` returned nothing. New returns a `commit_token` (UUID hex) for log correlation. Returns `""` if the payload is empty (no-op commit).

### 18. `HealableAsyncResource` preserved verbatim

Production-critical async pool wrapper with epoch-based race-free self-healing. Copied byte-for-byte from `old_flows/artifacts/healable_resource.py` (only the logger import path was updated to the core logger, `odyss_ai_flows.core.utils.logger`). API and behavior unchanged.

### 19. `InMemoryBackend` test double

Added under `tests/artifact_helpers.py`. Implements the `Backend` protocol with plain Python dicts. Lets every scenario validate the manager without a live DB. Same scenarios can be retargeted at `AzureSQLBackend` when a DSN is available.
