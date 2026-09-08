import json
import uuid
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Sequence, Tuple

import aioodbc.connection as _c
from aioodbc import create_pool

from odyss_ai_flows.core.utils.logger import logger

from odyss_ai_flows_artifacts.backends import register_backend
from odyss_ai_flows_artifacts.backends.azure_sql.healable_resource import (
    HealableAsyncResource,
)
from odyss_ai_flows_artifacts.backends.azure_sql.schema import (
    safe_ident as _safe_ident,
    schema_statements,
)
from odyss_ai_flows_artifacts.backends.base import (
    ArtifactRow,
    Backend,
    CommitPayload,
    JournalEntry,
)
from odyss_ai_flows_artifacts.metadata import (
    MetadataValue,
    deserialize_metadata_value,
    serialize_metadata_value,
)
from odyss_ai_flows_artifacts.query import JournalFilter, RelFilter
from odyss_ai_flows_artifacts.relationship import (
    REL_DERIVED_FROM,
    ArtifactRelationship,
)


# Silence unclosed connection warnings from aioodbc.
_OrigConn = _c.Connection


def _silent_del(self):
    try:
        if not self.closed:
            self._conn.close()
            self._conn = None
    except Exception:
        pass


_OrigConn.__del__ = _silent_del


def _placeholders(n: int) -> str:
    return ",".join(["?"] * n)


class _Executor:
    def __init__(self, pool):
        self._pool = pool

    async def close(self):
        self._pool.close()
        await self._pool.wait_closed()

    async def fetch_all(self, sql: str, params: Tuple = ()):
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, params)
                return await cur.fetchall()

    async def execute(self, sql: str, params: Tuple = ()):
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, params)

    async def execute_many(self, queries: Sequence[Tuple[str, Tuple]]):
        if not queries:
            return
        batches: "OrderedDict[str, List[Tuple]]" = OrderedDict()
        for sql, params in queries:
            batches.setdefault(sql, []).append(params)
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SET XACT_ABORT ON")
                for sql, param_sets in batches.items():
                    for i in range(0, len(param_sets), 200):
                        chunk = param_sets[i:i + 200]
                        if len(chunk) == 1:
                            await cur.execute(sql, chunk[0])
                        else:
                            await cur.executemany(sql, chunk)
            await conn.commit()


class AzureSQLBackend(Backend):
    def __init__(
        self,
        dsn: str,
        *,
        schema: Optional[str] = None,
        min_pool_size: int = 3,
        max_pool_size: int = 5,
        extra_indexes: Optional[List[Dict[str, Any]]] = None,
    ):
        self._dsn = dsn
        self._schema = schema
        self._minsize = min_pool_size
        self._maxsize = max_pool_size
        self._extra_indexes = extra_indexes or []
        self._auto = HealableAsyncResource(
            resource_factory=self._auto_factory, max_retries=1,
        )
        self._tx = HealableAsyncResource(
            resource_factory=self._tx_factory, max_retries=1,
        )
        self._owns_pools = True

    def with_schema(self, schema: Optional[str]) -> "AzureSQLBackend":
        if schema == self._schema:
            return self
        # Shallow __dict__ copy intentionally shares _auto/_tx (the pools).
        # Any mutable per-instance state added later must be re-bound here.
        view = object.__new__(AzureSQLBackend)
        view.__dict__.update(self.__dict__)
        view._schema = schema
        view._owns_pools = False
        return view

    async def _auto_factory(self):
        logger.info(
            "[azure_sql][POOL] autocommit=True min=%s max=%s",
            self._minsize, self._maxsize,
        )
        pool = await create_pool(
            dsn=self._dsn,
            autocommit=True,
            minsize=self._minsize,
            maxsize=self._maxsize,
            pool_recycle=900,
        )
        return _Executor(pool)

    async def _tx_factory(self):
        logger.info(
            "[azure_sql][POOL] autocommit=False min=%s max=%s",
            self._minsize, self._maxsize,
        )
        pool = await create_pool(
            dsn=self._dsn,
            autocommit=False,
            minsize=self._minsize,
            maxsize=self._maxsize,
            pool_recycle=900,
        )
        return _Executor(pool)

    def _t(self, table: str) -> str:
        return f"{self._schema}.{table}" if self._schema else table

    async def close(self) -> None:
        if not self._owns_pools:
            return
        try:
            await self._auto.close()
        except Exception:
            logger.exception("[azure_sql] error closing autocommit pool")
        try:
            await self._tx.close()
        except Exception:
            logger.exception("[azure_sql] error closing tx pool")

    async def init_schema(self) -> None:
        for sql in schema_statements(self._schema, self._extra_indexes):
            await self._auto.execute(sql)

    async def get_artifacts(
        self,
        ids: Sequence[str],
        *,
        include_deleted: bool = False,
    ) -> List[ArtifactRow]:
        ids = list(ids)
        if not ids:
            return []
        where = [f"id IN ({_placeholders(len(ids))})"]
        if not include_deleted:
            where.append("is_deleted = 0")
        sql = (
            f"SELECT id, alias, adapter_name, uri, origin_operation_id, "
            f"is_deleted, deleted_at FROM {self._t('artifacts')} "
            f"WHERE {' AND '.join(where)}"
        )
        rows = await self._auto.fetch_all(sql, tuple(ids))
        result_ids = [r[0] for r in rows]
        tags_by_id = await self._tags_for(result_ids)
        return [
            ArtifactRow(
                id=r[0],
                alias=r[1],
                adapter_name=r[2],
                uri=r[3],
                origin_operation_id=r[4],
                tags=tags_by_id.get(r[0], []),
                is_deleted=bool(r[5]),
                deleted_at=r[6],
            )
            for r in rows
        ]

    async def _tags_for(self, ids: Sequence[str]) -> Dict[str, List[str]]:
        ids = list(ids)
        if not ids:
            return {}
        rows = await self._auto.fetch_all(
            f"SELECT artifact_id, tag FROM {self._t('artifact_tags')} "
            f"WHERE artifact_id IN ({_placeholders(len(ids))})",
            tuple(ids),
        )
        tags_by_id: Dict[str, List[str]] = {}
        for aid, tag in rows:
            tags_by_id.setdefault(aid, []).append(tag)
        return tags_by_id

    async def query_artifact_ids(
        self,
        *,
        filters: Dict[str, Any],
        include_deleted: bool = False,
    ) -> List[str]:
        t_a = self._t("artifacts")
        t_t = self._t("artifact_tags")
        t_r = self._t("artifact_relationships")
        t_j = self._t("artifact_journal")
        where: List[str] = []
        params: List[Any] = []

        alias = filters.get("alias")
        if alias is not None:
            where.append("a.alias = ?")
            params.append(alias)
        origin_op = filters.get("origin_operation_id")
        if origin_op is not None:
            where.append("a.origin_operation_id = ?")
            params.append(origin_op)
        adapter_name = filters.get("adapter_name")
        if adapter_name is not None:
            where.append("a.adapter_name = ?")
            params.append(adapter_name)
        uri = filters.get("uri")
        if uri is not None:
            where.append("a.uri = ?")
            params.append(uri)
        tags = filters.get("tags")
        if tags is not None:
            tag_list = [tags] if isinstance(tags, str) else list(tags)
            for t in tag_list:
                where.append(
                    f"EXISTS (SELECT 1 FROM {t_t} t "
                    f"WHERE t.artifact_id = a.id AND t.tag = ?)"
                )
                params.append(t)

        # Relationship filters — one EXISTS per id (AND-of-many).
        # REL_DERIVED_FROM edge follows the verb: child --derived_from--> parent
        # (from_id = derived/child, to_id = origin/parent).
        # children_of: a --REL_DERIVED_FROM--> pid   (a is derived from pid)
        for pid in set(filters.get("children_of") or []):
            where.append(
                f"EXISTS (SELECT 1 FROM {t_r} r "
                f"WHERE r.from_id = a.id AND r.to_id = ? "
                f"AND r.relationship_type = ?)"
            )
            params.extend([pid, REL_DERIVED_FROM])
        # parents_of: cid --REL_DERIVED_FROM--> a   (a is the origin of cid)
        for cid in set(filters.get("parents_of") or []):
            where.append(
                f"EXISTS (SELECT 1 FROM {t_r} r "
                f"WHERE r.to_id = a.id AND r.from_id = ? "
                f"AND r.relationship_type = ?)"
            )
            params.extend([cid, REL_DERIVED_FROM])
        # Generic relationships
        for rf in (filters.get("related") or []):
            if not isinstance(rf, RelFilter):
                raise TypeError(
                    f"related[] expects RelFilter, got {type(rf).__name__}"
                )
            if rf.to_id is not None:
                where.append(
                    f"EXISTS (SELECT 1 FROM {t_r} r "
                    f"WHERE r.from_id = a.id AND r.to_id = ? "
                    f"AND r.relationship_type = ?)"
                )
                params.extend([rf.to_id, rf.type])
            else:
                where.append(
                    f"EXISTS (SELECT 1 FROM {t_r} r "
                    f"WHERE r.to_id = a.id AND r.from_id = ? "
                    f"AND r.relationship_type = ?)"
                )
                params.extend([rf.from_id, rf.type])

        # Journal filter — single EXISTS, fields ANDed.
        journal = filters.get("journal")
        if journal is not None:
            if not isinstance(journal, JournalFilter):
                raise TypeError(
                    f"journal expects JournalFilter, got {type(journal).__name__}"
                )
            conds = ["j.artifact_id = a.id"]
            if journal.entry_type is not None:
                conds.append("j.entry_type = ?")
                params.append(journal.entry_type)
            if journal.before is not None:
                conds.append("j.timestamp <= ?")
                params.append(journal.before)
            if journal.after is not None:
                conds.append("j.timestamp >= ?")
                params.append(journal.after)
            where.append(
                f"EXISTS (SELECT 1 FROM {t_j} j WHERE {' AND '.join(conds)})"
            )

        if not include_deleted:
            where.append("a.is_deleted = 0")

        sql = f"SELECT a.id FROM {t_a} a"
        if where:
            sql += " WHERE " + " AND ".join(where)
        rows = await self._auto.fetch_all(sql, tuple(params))
        return [r[0] for r in rows]

    async def query_relationships(
        self,
        *,
        from_id: Optional[str] = None,
        to_id: Optional[str] = None,
        relationship_type: Optional[str] = None,
    ) -> List[ArtifactRelationship]:
        where = []
        params: List[Any] = []
        if from_id is not None:
            where.append("from_id = ?")
            params.append(from_id)
        if to_id is not None:
            where.append("to_id = ?")
            params.append(to_id)
        if relationship_type is not None:
            where.append("relationship_type = ?")
            params.append(relationship_type)
        sql = (
            f"SELECT from_id, to_id, relationship_type, "
            f"metadata_json, created_at FROM {self._t('artifact_relationships')}"
        )
        if where:
            sql += " WHERE " + " AND ".join(where)
        rows = await self._auto.fetch_all(sql, tuple(params))
        return [
            ArtifactRelationship(
                from_id=r[0],
                to_id=r[1],
                relationship_type=r[2],
                metadata=json.loads(r[3]) if r[3] else None,
                created_at=r[4],
            )
            for r in rows
        ]

    async def get_metadata_bulk(
        self,
        artifact_ids: Sequence[str],
        keys: Optional[Sequence[str]] = None,
    ) -> Dict[str, Dict[str, MetadataValue]]:
        ids = list(artifact_ids)
        if not ids:
            return {}
        where = [f"artifact_id IN ({_placeholders(len(ids))})"]
        params: List[Any] = list(ids)
        if keys is not None:
            keys = list(keys)
            if not keys:
                return {aid: {} for aid in ids}
            where.append(f"meta_key IN ({_placeholders(len(keys))})")
            params.extend(keys)
        sql = (
            f"SELECT artifact_id, meta_key, meta_value, meta_type "
            f"FROM {self._t('artifact_metadata')} "
            f"WHERE {' AND '.join(where)}"
        )
        rows = await self._auto.fetch_all(sql, tuple(params))
        result: Dict[str, Dict[str, MetadataValue]] = {aid: {} for aid in ids}
        for aid, key, raw, type_tag in rows:
            result.setdefault(aid, {})[key] = deserialize_metadata_value(
                raw, type_tag,
            )
        return result

    async def query_journal_entries(
        self,
        *,
        artifact_id: Optional[str] = None,
        entry_type: Optional[str] = None,
        before=None,
        after=None,
    ) -> List[JournalEntry]:
        where = []
        params: List[Any] = []
        if artifact_id is not None:
            where.append("artifact_id = ?")
            params.append(artifact_id)
        if entry_type is not None:
            where.append("entry_type = ?")
            params.append(entry_type)
        if before is not None:
            where.append("timestamp <= ?")
            params.append(before)
        if after is not None:
            where.append("timestamp >= ?")
            params.append(after)
        sql = (
            f"SELECT artifact_id, timestamp, entry_type, content "
            f"FROM {self._t('artifact_journal')}"
        )
        if where:
            sql += " WHERE " + " AND ".join(where)
        rows = await self._auto.fetch_all(sql, tuple(params))
        return [
            JournalEntry(
                artifact_id=r[0],
                timestamp=r[1],
                entry_type=r[2],
                content=r[3],
            )
            for r in rows
        ]

    async def commit(self, payload: CommitPayload) -> str:
        queries: List[Tuple[str, Tuple]] = []

        t_a = self._t("artifacts")
        t_t = self._t("artifact_tags")
        t_r = self._t("artifact_relationships")
        t_m = self._t("artifact_metadata")
        t_j = self._t("artifact_journal")

        for row in payload.artifact_creates:
            queries.append((
                f"INSERT INTO {t_a} "
                f"(id, alias, adapter_name, uri, origin_operation_id) "
                f"VALUES (?, ?, ?, ?, ?)",
                (
                    row.id, row.alias, row.adapter_name, row.uri,
                    row.origin_operation_id,
                ),
            ))
            for tag in row.tags:
                queries.append((
                    f"INSERT INTO {t_t} (artifact_id, tag) VALUES (?, ?)",
                    (row.id, tag),
                ))

        for upd in payload.artifact_field_updates:
            if not upd.fields:
                continue
            sets = ", ".join(f"{_safe_ident(k)} = ?" for k in upd.fields)
            params = tuple(upd.fields.values()) + (upd.id,)
            queries.append((
                f"UPDATE {t_a} SET {sets} WHERE id = ?",
                params,
            ))

        for rel in payload.relationship_adds:
            meta_json = (
                json.dumps(rel.metadata) if rel.metadata else None
            )
            queries.append((
                f"INSERT INTO {t_r} "
                f"(from_id, to_id, relationship_type, metadata_json) "
                f"VALUES (?, ?, ?, ?)",
                (rel.from_id, rel.to_id, rel.relationship_type, meta_json),
            ))

        for frm, to, rt in payload.relationship_deletes:
            queries.append((
                f"DELETE FROM {t_r} "
                f"WHERE from_id = ? AND to_id = ? AND relationship_type = ?",
                (frm, to, rt),
            ))

        for aid, key, value in payload.metadata_sets:
            raw, type_tag = serialize_metadata_value(value)
            queries.append((
                f"MERGE {t_m} AS target "
                f"USING (SELECT ? AS artifact_id, ? AS meta_key) AS source "
                f"ON target.artifact_id = source.artifact_id "
                f"AND target.meta_key = source.meta_key "
                f"WHEN MATCHED THEN UPDATE SET meta_value = ?, meta_type = ? "
                f"WHEN NOT MATCHED THEN INSERT "
                f"(artifact_id, meta_key, meta_value, meta_type) "
                f"VALUES (?, ?, ?, ?);",
                (aid, key, raw, type_tag, aid, key, raw, type_tag),
            ))

        for aid, key in payload.metadata_deletes:
            queries.append((
                f"DELETE FROM {t_m} WHERE artifact_id = ? AND meta_key = ?",
                (aid, key),
            ))

        for entry in payload.journal_entries:
            queries.append((
                f"INSERT INTO {t_j} (artifact_id, entry_type, content) "
                f"VALUES (?, ?, ?)",
                (entry.artifact_id, entry.entry_type, entry.content),
            ))

        await self._tx.execute_many(queries)
        return uuid.uuid4().hex

    async def soft_delete_artifacts(self, ids: Sequence[str]) -> None:
        ids = list(ids)
        if not ids:
            return
        queries = [
            (
                f"UPDATE {self._t('artifacts')} "
                f"SET is_deleted = 1, deleted_at = SYSUTCDATETIME() WHERE id = ?",
                (aid,),
            )
            for aid in ids
        ]
        await self._tx.execute_many(queries)

    async def hard_delete_artifacts(self, ids: Sequence[str]) -> None:
        ids = list(ids)
        if not ids:
            return
        t_a = self._t("artifacts")
        t_t = self._t("artifact_tags")
        t_r = self._t("artifact_relationships")
        t_m = self._t("artifact_metadata")
        t_j = self._t("artifact_journal")
        queries: List[Tuple[str, Tuple]] = []
        for aid in ids:
            queries.append((
                f"DELETE FROM {t_t} WHERE artifact_id = ?", (aid,),
            ))
            queries.append((
                f"DELETE FROM {t_m} WHERE artifact_id = ?", (aid,),
            ))
            queries.append((
                f"DELETE FROM {t_j} WHERE artifact_id = ?", (aid,),
            ))
            queries.append((
                f"DELETE FROM {t_r} WHERE from_id = ? OR to_id = ?",
                (aid, aid),
            ))
            queries.append((
                f"DELETE FROM {t_a} WHERE id = ?", (aid,),
            ))
        await self._tx.execute_many(queries)

    async def restore_artifacts(self, ids: Sequence[str]) -> None:
        ids = list(ids)
        if not ids:
            return
        queries = [
            (
                f"UPDATE {self._t('artifacts')} "
                f"SET is_deleted = 0, deleted_at = NULL WHERE id = ?",
                (aid,),
            )
            for aid in ids
        ]
        await self._tx.execute_many(queries)


register_backend("azure_sql", AzureSQLBackend)
