from __future__ import annotations

import asyncio
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
)

from odyss_ai_flows.core.utils.logger import logger

from odyss_ai_flows_artifacts.adapter_registry import AdapterRegistry
from odyss_ai_flows_artifacts.artifact import Artifact
from odyss_ai_flows_artifacts.backends import (
    Backend,
    CommitPayload,
    JournalEntry,
    get_backend_factory,
)
from odyss_ai_flows_artifacts.backends.base import ArtifactRow
from odyss_ai_flows_artifacts.metadata import (
    MetadataValue,
    validate_metadata_value,
)
from odyss_ai_flows_artifacts.query import (
    ArtifactQuery,
    JournalFilter,
    RelFilter,
)
from odyss_ai_flows_artifacts.relationship import (
    REL_DERIVED_FROM,
    ArtifactRelationship,
)


_shared_backends: Dict[str, Tuple[Backend, AdapterRegistry]] = {}
_shared_backends_lock = asyncio.Lock()

_META_KEYS = frozenset({
    "backend", "adapters_path", "adapter_mapping",
})


async def _resolve_artifact_config() -> Optional[Tuple[str, Dict[str, Any]]]:
    try:
        from odyss_ai_flows import cget
        from odyss_ai_flows.core.config.profiles import select_profile
    except ImportError:
        return None

    cfg = await cget("artifact_config", default=None)
    if not cfg:
        return None

    if not isinstance(cfg, dict):
        raise TypeError(
            f"artifact_config must be a dict; got {type(cfg).__name__}."
        )

    # Legacy single-pool flat shape is the one that carries its OWN `am_name`
    # field inside the block (the sibling selector is ignored in that mode).
    # The whole block is then one pool keyed by that field.
    if cfg.get("am_name"):
        am_name = cfg["am_name"]
        pool_cfg = {k: v for k, v in cfg.items() if k != "am_name"}
        return am_name, pool_cfg

    # Registry form — same named-profile resolution used for LLM connections:
    # dict values are pools and scalar siblings overlay the selected pool.
    selector = await cget("am_name", default=None)
    return select_profile(
        cfg,
        selector,
        config_label="artifact_config",
        selector_label="am_name",
    )


async def close_all_shared_backends() -> None:
    async with _shared_backends_lock:
        for backend, _ in _shared_backends.values():
            try:
                await backend.close()
            except Exception:
                logger.exception(
                    "[ArtifactManager] close_all_shared_backends: "
                    "backend close failed"
                )
        _shared_backends.clear()


class ArtifactManager:
    def __init__(
        self,
        schema: Optional[str] = None,
        *,
        backend: Optional[Backend] = None,
        adapter_registry: Optional[AdapterRegistry] = None,
        default_origin_operation_id: Optional[str] = None,
    ):
        self.schema = schema
        self.adapter_registry = adapter_registry
        self.default_origin_operation_id = default_origin_operation_id
        self._owns_backend = False
        if backend is not None and schema is not None:
            self.backend: Optional[Backend] = backend.with_schema(schema)
        else:
            self.backend = backend
        self._init_lock = asyncio.Lock()

        self._staged_artifacts: Dict[str, Artifact] = {}
        self._artifact_cache: Dict[str, Artifact] = {}
        self._staged_relationship_adds: List[ArtifactRelationship] = []
        self._staged_relationship_deletes: List[Tuple[str, str, str]] = []
        self._staged_metadata_sets: Dict[Tuple[str, str], MetadataValue] = {}
        self._staged_metadata_deletes: Set[Tuple[str, str]] = set()
        self._staged_journal_entries: List[JournalEntry] = []
        self._dirty_artifacts: Set[str] = set()

    @classmethod
    def from_config(
        cls,
        config: Dict[str, Any],
        *,
        default_origin_operation_id: Optional[str] = None,
    ) -> "ArtifactManager":
        backend_name = config.get("backend", "azure_sql")
        backend_args = config.get("backend_args", {})
        backend = get_backend_factory(backend_name)(**backend_args)
        registry = AdapterRegistry(
            adapters_path=config.get("adapters_path"),
            adapter_mapping=config.get("adapter_mapping"),
        )
        instance = cls(
            backend=backend,
            adapter_registry=registry,
            default_origin_operation_id=default_origin_operation_id,
        )
        instance._owns_backend = True
        return instance

    async def aclose(self) -> None:
        if self._owns_backend and self.backend is not None:
            await self.backend.close()

    async def _ensure_initialized(self) -> None:
        if self.backend is not None:
            return
        async with self._init_lock:
            if self.backend is not None:
                return
            resolved = await _resolve_artifact_config()
            if resolved is None:
                raise RuntimeError(
                    "ArtifactManager: no 'artifact_config' resolvable. "
                    "Either pass backend= explicitly, use "
                    "ArtifactManager.from_config(...), or define an "
                    "artifact_config registry in global_config.json (or a "
                    "closer config.json)."
                )
            am_name, cfg = resolved
            base_backend, _shared_registry = await self._get_or_create_shared(
                am_name, cfg,
            )
            self.backend = (
                base_backend.with_schema(self.schema)
                if self.schema is not None
                else base_backend
            )
            if self.adapter_registry is None:
                # Build the adapter registry from THIS scope's resolved config
                # (incl. any `adapters` overlay) rather than the one cached
                # under `am_name`. The backend/connection pool is still shared;
                # only the cheap, connectionless adapter registry is per-scope,
                # so a nested `adapters` override actually takes effect even
                # when another scope resolved the same pool first.
                self.adapter_registry = AdapterRegistry(
                    adapters_path=cfg.get("adapters_path"),
                    adapter_mapping=cfg.get("adapter_mapping"),
                )

    @staticmethod
    async def _get_or_create_shared(
        am_name: str,
        cfg: Dict[str, Any],
    ) -> Tuple[Backend, AdapterRegistry]:
        cached = _shared_backends.get(am_name)
        if cached is not None:
            return cached
        async with _shared_backends_lock:
            cached = _shared_backends.get(am_name)
            if cached is not None:
                return cached
            if "backend_args" in cfg:
                raise ValueError(
                    "artifact_config takes flat backend kwargs (e.g. dsn=...), "
                    "not a nested 'backend_args' block — that form is for "
                    "ArtifactManager.from_config(...)."
                )
            backend_name = cfg.get("backend", "azure_sql")
            backend_kwargs = {
                k: v for k, v in cfg.items() if k not in _META_KEYS
            }
            backend = get_backend_factory(backend_name)(**backend_kwargs)
            registry = AdapterRegistry(
                adapters_path=cfg.get("adapters_path"),
                adapter_mapping=cfg.get("adapter_mapping"),
            )
            _shared_backends[am_name] = (backend, registry)
            return _shared_backends[am_name]

    def __getattr__(self, name: str):
        if name.startswith("create_") and name != "create_artifact":
            adapter_name = name[len("create_"):]

            async def creator(**kwargs):
                await self._ensure_initialized()
                if adapter_name not in self.adapter_registry.known_names():
                    raise AttributeError(name)
                return await self.create_artifact(
                    adapter_name=adapter_name, **kwargs,
                )
            return creator
        raise AttributeError(name)

    async def create(self, adapter_name: Optional[str] = None, **kwargs) -> Artifact:
        return await self.create_artifact(adapter_name=adapter_name, **kwargs)

    async def create_artifact(
        self,
        *,
        alias: Optional[str] = None,
        adapter_name: Optional[str] = None,
        uri: Optional[str] = None,
        origin_operation_id: Optional[str] = None,
        tags: Optional[Iterable[str]] = None,
    ) -> Artifact:
        await self._ensure_initialized()
        artifact = Artifact(
            alias=alias,
            adapter_name=adapter_name,
            uri=uri,
            origin_operation_id=origin_operation_id or self.default_origin_operation_id,
            tags=tags,
            manager=self,
        )
        self._staged_artifacts[artifact.id] = artifact
        self._dirty_artifacts.add(artifact.id)
        return artifact

    async def get_artifact(
        self,
        artifact_id: Union[str, ArtifactQuery],
        *,
        include_staged: bool = True,
        include_deleted: bool = False,
    ) -> Optional[Artifact]:
        if isinstance(artifact_id, ArtifactQuery):
            results = await self.query_artifacts(
                artifact_id,
                include_staged=include_staged,
                include_deleted=include_deleted,
            )
            return results[0] if results else None
        results = await self.get_artifacts(
            [artifact_id],
            include_staged=include_staged,
            include_deleted=include_deleted,
        )
        return results[0] if results else None

    async def get_artifacts(
        self,
        ids: Sequence[str],
        *,
        include_staged: bool = True,
        include_deleted: bool = False,
    ) -> List[Artifact]:
        ids = list(ids)
        if not ids:
            return []
        await self._ensure_initialized()
        result_map: Dict[str, Artifact] = {}
        to_fetch: List[str] = []
        for aid in ids:
            if include_staged and aid in self._staged_artifacts:
                a = self._staged_artifacts[aid]
                if include_deleted or not a.is_deleted:
                    result_map[aid] = a
                continue
            if include_staged and aid in self._artifact_cache:
                a = self._artifact_cache[aid]
                if include_deleted or not a.is_deleted:
                    result_map[aid] = a
                continue
            to_fetch.append(aid)

        if to_fetch:
            rows = await self.backend.get_artifacts(
                to_fetch, include_deleted=include_deleted,
            )
            metas = await self.backend.get_metadata_bulk(to_fetch)
            for row in rows:
                a = self._hydrate(row)
                a.metadata = dict(metas.get(row.id, {}))
                if include_staged:
                    self._apply_staged_metadata_overlay(a)
                result_map[row.id] = a

        return [result_map[aid] for aid in ids if aid in result_map]

    @staticmethod
    def _as_query(
        query: Optional[ArtifactQuery],
        **kwargs: Any,
    ) -> ArtifactQuery:
        if query is not None:
            if any(v is not None for v in kwargs.values()):
                raise TypeError(
                    "pass either an ArtifactQuery or keyword filters, not both"
                )
            return query
        return ArtifactQuery(**kwargs)

    async def query_artifact_ids(
        self,
        query: Optional[ArtifactQuery] = None,
        *,
        alias: Optional[str] = None,
        origin_operation_id: Optional[str] = None,
        adapter_name: Optional[str] = None,
        uri: Optional[str] = None,
        tags: Optional[Iterable[str]] = None,
        children_of: Optional[Iterable[str]] = None,
        parents_of: Optional[Iterable[str]] = None,
        related: Optional[Iterable[RelFilter]] = None,
        journal: Optional[JournalFilter] = None,
        include_staged: bool = True,
        include_deleted: bool = False,
    ) -> List[str]:
        query = self._as_query(
            query,
            alias=alias,
            origin_operation_id=origin_operation_id,
            adapter_name=adapter_name,
            uri=uri,
            tags=list(tags) if tags is not None else None,
            children_of=list(children_of) if children_of else None,
            parents_of=list(parents_of) if parents_of else None,
            related=list(related) if related else None,
            journal=journal,
        )
        await self._ensure_initialized()
        filters: Dict[str, Any] = query.to_filters()
        backend_ids = await self.backend.query_artifact_ids(
            filters=filters, include_deleted=include_deleted,
        )
        if not include_staged:
            return list(backend_ids)
        result = set(backend_ids)
        for a in self._staged_artifacts.values():
            if include_deleted or not a.is_deleted:
                if self._match_filters(a, filters):
                    result.add(a.id)
        return list(result)

    async def query_artifacts(
        self,
        query: Optional[ArtifactQuery] = None,
        *,
        alias: Optional[str] = None,
        origin_operation_id: Optional[str] = None,
        adapter_name: Optional[str] = None,
        uri: Optional[str] = None,
        tags: Optional[Iterable[str]] = None,
        children_of: Optional[Iterable[str]] = None,
        parents_of: Optional[Iterable[str]] = None,
        related: Optional[Iterable[RelFilter]] = None,
        journal: Optional[JournalFilter] = None,
        include_staged: bool = True,
        include_deleted: bool = False,
    ) -> List[Artifact]:
        query = self._as_query(
            query,
            alias=alias,
            origin_operation_id=origin_operation_id,
            adapter_name=adapter_name,
            uri=uri,
            tags=list(tags) if tags is not None else None,
            children_of=list(children_of) if children_of else None,
            parents_of=list(parents_of) if parents_of else None,
            related=list(related) if related else None,
            journal=journal,
        )
        ids = await self.query_artifact_ids(
            query,
            include_staged=include_staged,
            include_deleted=include_deleted,
        )
        return await self.get_artifacts(
            ids,
            include_staged=include_staged,
            include_deleted=include_deleted,
        )

    async def delete_artifact(self, artifact_id: str, *, hard: bool = False) -> None:
        await self.delete_artifacts([artifact_id], hard=hard)

    async def delete_artifacts(
        self,
        ids: Sequence[str],
        *,
        hard: bool = False,
    ) -> None:
        ids = list(ids)
        if not ids:
            return
        await self._ensure_initialized()
        target = set(ids)
        had_pending = self._purge_staged_for(target)
        if had_pending:
            logger.warning(
                "[ArtifactManager] purged pending staged changes for deleted ids=%r",
                sorted(target),
            )
        if hard:
            await self.backend.hard_delete_artifacts(ids)
            for aid in ids:
                self._artifact_cache.pop(aid, None)
        else:
            await self.backend.soft_delete_artifacts(ids)
            for aid in ids:
                cached = self._artifact_cache.get(aid)
                if cached is not None:
                    cached.is_deleted = True

    async def restore_artifact(self, artifact_id: str) -> None:
        await self.restore_artifacts([artifact_id])

    async def restore_artifacts(self, ids: Sequence[str]) -> None:
        ids = list(ids)
        if not ids:
            return
        await self._ensure_initialized()
        await self.backend.restore_artifacts(ids)
        for aid in ids:
            cached = self._artifact_cache.get(aid)
            if cached is not None:
                cached.is_deleted = False

    async def add_relationship(
        self,
        from_id: str,
        to_id: str,
        relationship_type: str,
        metadata: Optional[Dict[str, MetadataValue]] = None,
    ) -> None:
        if metadata is not None:
            for v in metadata.values():
                validate_metadata_value(v)
        self._staged_relationship_adds.append(
            ArtifactRelationship(
                from_id=from_id,
                to_id=to_id,
                relationship_type=relationship_type,
                metadata=dict(metadata) if metadata else None,
            )
        )
        self._dirty_artifacts.add(from_id)

    async def add_relationships(
        self,
        relationships: Iterable[ArtifactRelationship],
    ) -> None:
        for r in relationships:
            await self.add_relationship(
                r.from_id, r.to_id, r.relationship_type, r.metadata,
            )

    async def delete_relationship(
        self,
        from_id: str,
        to_id: str,
        relationship_type: str,
    ) -> None:
        self._staged_relationship_deletes.append(
            (from_id, to_id, relationship_type)
        )
        self._dirty_artifacts.add(from_id)

    async def query_relationships(
        self,
        *,
        from_id: Optional[str] = None,
        to_id: Optional[str] = None,
        relationship_type: Optional[str] = None,
        include_staged: bool = True,
    ) -> List[ArtifactRelationship]:
        await self._ensure_initialized()
        committed = await self.backend.query_relationships(
            from_id=from_id,
            to_id=to_id,
            relationship_type=relationship_type,
        )
        if not include_staged:
            return committed
        deleted = set(self._staged_relationship_deletes)
        result = [
            r for r in committed
            if (r.from_id, r.to_id, r.relationship_type) not in deleted
        ]
        for r in self._staged_relationship_adds:
            if from_id is not None and r.from_id != from_id:
                continue
            if to_id is not None and r.to_id != to_id:
                continue
            if relationship_type is not None and r.relationship_type != relationship_type:
                continue
            if (r.from_id, r.to_id, r.relationship_type) in deleted:
                continue
            result.append(r)
        return result

    async def query_outgoing_relationships(
        self,
        from_id: str,
        relationship_type: Optional[str] = None,
        *,
        include_staged: bool = True,
    ) -> List[ArtifactRelationship]:
        return await self.query_relationships(
            from_id=from_id,
            relationship_type=relationship_type,
            include_staged=include_staged,
        )

    async def query_incoming_relationships(
        self,
        to_id: str,
        relationship_type: Optional[str] = None,
        *,
        include_staged: bool = True,
    ) -> List[ArtifactRelationship]:
        return await self.query_relationships(
            to_id=to_id,
            relationship_type=relationship_type,
            include_staged=include_staged,
        )

    async def parent_relationships(
        self, artifact_id: str,
    ) -> List[ArtifactRelationship]:
        # Outgoing derived_from: artifact_id --derived_from--> parent.
        return await self.query_outgoing_relationships(
            artifact_id, REL_DERIVED_FROM,
        )

    async def child_relationships(
        self, artifact_id: str,
    ) -> List[ArtifactRelationship]:
        # Incoming derived_from: child --derived_from--> artifact_id.
        return await self.query_incoming_relationships(
            artifact_id, REL_DERIVED_FROM,
        )

    async def set_metadata(
        self,
        artifact_id: str,
        key: str,
        value: MetadataValue,
    ) -> None:
        validate_metadata_value(value)
        self._staged_metadata_sets[(artifact_id, key)] = value
        self._staged_metadata_deletes.discard((artifact_id, key))
        self._dirty_artifacts.add(artifact_id)
        a = (
            self._staged_artifacts.get(artifact_id)
            or self._artifact_cache.get(artifact_id)
        )
        if a is not None:
            a.metadata[key] = value

    async def set_metadata_bulk(
        self,
        artifact_id: str,
        mapping: Dict[str, MetadataValue],
    ) -> None:
        for v in mapping.values():
            validate_metadata_value(v)
        for k, v in mapping.items():
            await self.set_metadata(artifact_id, k, v)

    async def delete_metadata(self, artifact_id: str, key: str) -> None:
        self._staged_metadata_sets.pop((artifact_id, key), None)
        self._staged_metadata_deletes.add((artifact_id, key))
        self._dirty_artifacts.add(artifact_id)
        a = (
            self._staged_artifacts.get(artifact_id)
            or self._artifact_cache.get(artifact_id)
        )
        if a is not None:
            a.metadata.pop(key, None)

    async def delete_metadata_bulk(self, pairs: Iterable[Tuple[str, str]]) -> None:
        for aid, key in pairs:
            await self.delete_metadata(aid, key)

    async def get_metadata_bulk(
        self,
        artifact_ids: Sequence[str],
        keys: Optional[Sequence[str]] = None,
        *,
        include_staged: bool = True,
    ) -> Dict[str, Dict[str, MetadataValue]]:
        ids = list(artifact_ids)
        await self._ensure_initialized()
        committed_only = [aid for aid in ids if aid not in self._staged_artifacts]
        committed = await self.backend.get_metadata_bulk(committed_only, keys)
        result: Dict[str, Dict[str, MetadataValue]] = {
            aid: dict(committed.get(aid, {})) for aid in ids
        }
        if not include_staged:
            return result
        for aid in ids:
            a = self._staged_artifacts.get(aid)
            if a is not None:
                for k, v in a.metadata.items():
                    if keys is not None and k not in keys:
                        continue
                    result[aid][k] = v
        for (aid, k), v in self._staged_metadata_sets.items():
            if aid not in result:
                continue
            if keys is not None and k not in keys:
                continue
            result[aid][k] = v
        for (aid, k) in self._staged_metadata_deletes:
            if aid in result:
                result[aid].pop(k, None)
        return result

    async def add_journal_entry(
        self,
        artifact_id: str,
        content: str,
        entry_type: Optional[str] = None,
    ) -> None:
        if self.default_origin_operation_id:
            content = (
                f"Operation ID: {self.default_origin_operation_id}. {content}"
            )
        self._staged_journal_entries.append(
            JournalEntry(
                artifact_id=artifact_id,
                content=content,
                entry_type=entry_type,
            )
        )
        self._dirty_artifacts.add(artifact_id)

    async def add_journal_entries(
        self,
        entries: Iterable[JournalEntry],
    ) -> None:
        for e in entries:
            await self.add_journal_entry(
                e.artifact_id, e.content, e.entry_type,
            )

    async def query_journal_entries(
        self,
        *,
        artifact_id: Optional[str] = None,
        entry_type: Optional[str] = None,
        before=None,
        after=None,
        include_staged: bool = True,
    ) -> List[JournalEntry]:
        await self._ensure_initialized()
        committed = await self.backend.query_journal_entries(
            artifact_id=artifact_id,
            entry_type=entry_type,
            before=before,
            after=after,
        )
        if not include_staged:
            return committed
        result = list(committed)
        for e in self._staged_journal_entries:
            if artifact_id is not None and e.artifact_id != artifact_id:
                continue
            if entry_type is not None and e.entry_type != entry_type:
                continue
            result.append(e)
        return result

    async def commit(self) -> str:
        payload = CommitPayload(
            artifact_creates=[
                ArtifactRow(
                    id=a.id,
                    alias=a.alias,
                    adapter_name=a.adapter_name,
                    uri=a.uri,
                    origin_operation_id=a.origin_operation_id,
                    tags=sorted(a.tags),
                )
                for a in self._staged_artifacts.values()
            ],
            relationship_adds=list(self._staged_relationship_adds),
            relationship_deletes=list(self._staged_relationship_deletes),
            metadata_sets=[
                (aid, k, v)
                for (aid, k), v in self._staged_metadata_sets.items()
            ],
            metadata_deletes=list(self._staged_metadata_deletes),
            journal_entries=list(self._staged_journal_entries),
        )
        if payload.is_empty():
            return ""
        # Backend is only needed once we actually have something to persist.
        await self._ensure_initialized()
        token = await self.backend.commit(payload)
        for aid, a in list(self._staged_artifacts.items()):
            self._artifact_cache[aid] = a
        self._clear_staging()
        return token

    def rollback(self) -> None:
        self._clear_staging()

    def _clear_staging(self) -> None:
        self._staged_artifacts.clear()
        self._staged_relationship_adds.clear()
        self._staged_relationship_deletes.clear()
        self._staged_metadata_sets.clear()
        self._staged_metadata_deletes.clear()
        self._staged_journal_entries.clear()
        self._dirty_artifacts.clear()

    def _purge_staged_for(self, ids: Set[str]) -> bool:
        had_pending = False
        for aid in list(self._staged_artifacts):
            if aid in ids:
                self._staged_artifacts.pop(aid)
                had_pending = True
        before_meta_sets = len(self._staged_metadata_sets)
        self._staged_metadata_sets = {
            k: v for k, v in self._staged_metadata_sets.items()
            if k[0] not in ids
        }
        if len(self._staged_metadata_sets) != before_meta_sets:
            had_pending = True
        before_meta_deletes = len(self._staged_metadata_deletes)
        self._staged_metadata_deletes = {
            k for k in self._staged_metadata_deletes if k[0] not in ids
        }
        if len(self._staged_metadata_deletes) != before_meta_deletes:
            had_pending = True
        before_rel_adds = len(self._staged_relationship_adds)
        self._staged_relationship_adds = [
            r for r in self._staged_relationship_adds
            if r.from_id not in ids and r.to_id not in ids
        ]
        if len(self._staged_relationship_adds) != before_rel_adds:
            had_pending = True
        before_rel_dels = len(self._staged_relationship_deletes)
        self._staged_relationship_deletes = [
            t for t in self._staged_relationship_deletes
            if t[0] not in ids and t[1] not in ids
        ]
        if len(self._staged_relationship_deletes) != before_rel_dels:
            had_pending = True
        before_journal = len(self._staged_journal_entries)
        self._staged_journal_entries = [
            j for j in self._staged_journal_entries if j.artifact_id not in ids
        ]
        if len(self._staged_journal_entries) != before_journal:
            had_pending = True
        for aid in ids:
            self._dirty_artifacts.discard(aid)
        return had_pending

    def _hydrate(self, row: ArtifactRow) -> Artifact:
        adapter = None
        if row.adapter_name:
            try:
                adapter = self.adapter_registry.load(row.adapter_name)
            except LookupError:
                logger.warning(
                    "[ArtifactManager] adapter %r not loadable for artifact %s",
                    row.adapter_name, row.id,
                )
        artifact = Artifact.from_row(row, adapter=adapter, manager=self)
        self._artifact_cache[row.id] = artifact
        return artifact

    def _apply_staged_metadata_overlay(self, artifact: Artifact) -> None:
        for (aid, k), v in self._staged_metadata_sets.items():
            if aid == artifact.id:
                artifact.metadata[k] = v
        for (aid, k) in self._staged_metadata_deletes:
            if aid == artifact.id:
                artifact.metadata.pop(k, None)

    def _match_filters(self, artifact: Artifact, filters: Dict[str, Any]) -> bool:
        alias = filters.get("alias")
        if alias is not None and artifact.alias != alias:
            return False
        origin_op = filters.get("origin_operation_id")
        if origin_op is not None and artifact.origin_operation_id != origin_op:
            return False
        adapter_name = filters.get("adapter_name")
        if adapter_name is not None and artifact.adapter_name != adapter_name:
            return False
        uri = filters.get("uri")
        if uri is not None and artifact.uri != uri:
            return False
        tags = filters.get("tags")
        if tags is not None:
            required = {tags} if isinstance(tags, str) else set(tags)
            if not required.issubset(artifact.tags):
                return False
        children_of = filters.get("children_of")
        if children_of:
            # artifact is a child of p  <=>  artifact --derived_from--> p
            for pid in set(children_of):
                if not self._has_relationship_to(
                    artifact.id, pid, REL_DERIVED_FROM, outgoing=True,
                ):
                    return False
        parents_of = filters.get("parents_of")
        if parents_of:
            # artifact is a parent of c  <=>  c --derived_from--> artifact
            for cid in set(parents_of):
                if not self._has_relationship_to(
                    artifact.id, cid, REL_DERIVED_FROM, outgoing=False,
                ):
                    return False
        related = filters.get("related")
        if related:
            for rf in related:
                if rf.to_id is not None:
                    ok = self._has_relationship_to(
                        artifact.id, rf.to_id, rf.type, outgoing=True,
                    )
                else:
                    ok = self._has_relationship_to(
                        artifact.id, rf.from_id, rf.type, outgoing=False,
                    )
                if not ok:
                    return False
        journal = filters.get("journal")
        if journal is not None and not self._matches_journal(artifact.id, journal):
            return False
        return True

    def _has_relationship_to(
        self,
        artifact_id: str,
        peer_id: str,
        relationship_type: str,
        *,
        outgoing: bool,
    ) -> bool:
        frm, to = (
            (artifact_id, peer_id) if outgoing else (peer_id, artifact_id)
        )
        key = (frm, to, relationship_type)
        return any(
            (r.from_id, r.to_id, r.relationship_type) == key
            for r in self._staged_relationship_adds
        )

    def _matches_journal(self, artifact_id: str, jf: JournalFilter) -> bool:
        if jf.before is not None or jf.after is not None:
            return False
        for e in self._staged_journal_entries:
            if e.artifact_id != artifact_id:
                continue
            if jf.entry_type is not None and e.entry_type != jf.entry_type:
                continue
            return True
        return False
