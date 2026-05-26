from __future__ import annotations

import copy
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

from odyss_ai_flows_artifacts.backends.base import (
    ArtifactRow,
    Backend,
    CommitPayload,
    JournalEntry,
)
from odyss_ai_flows_artifacts.metadata import MetadataValue
from odyss_ai_flows_artifacts.relationship import ArtifactRelationship


class InMemoryBackend(Backend):
    """Pure-Python backend used by test scenarios."""

    def __init__(self):
        self.artifacts: Dict[str, ArtifactRow] = {}
        self.relationships: Dict[Tuple[str, str, str], ArtifactRelationship] = {}
        self.metadata: Dict[Tuple[str, str], Tuple[MetadataValue, str]] = {}
        self.journal: List[JournalEntry] = []
        self.commit_calls = 0

    async def init_schema(self) -> None:
        pass

    async def close(self) -> None:
        pass

    async def get_artifacts(
        self,
        ids: Sequence[str],
        *,
        include_deleted: bool = False,
    ) -> List[ArtifactRow]:
        out = []
        for aid in ids:
            row = self.artifacts.get(aid)
            if row is None:
                continue
            if row.is_deleted and not include_deleted:
                continue
            out.append(copy.deepcopy(row))
        return out

    async def query_artifact_ids(
        self,
        *,
        filters: Dict[str, Any],
        include_deleted: bool = False,
    ) -> List[str]:
        ids = []
        for row in self.artifacts.values():
            if row.is_deleted and not include_deleted:
                continue
            if filters.get("alias") is not None and row.alias != filters["alias"]:
                continue
            if filters.get("parent_operation_id") is not None and row.parent_operation_id != filters["parent_operation_id"]:
                continue
            if filters.get("adapter_name") is not None and row.adapter_name != filters["adapter_name"]:
                continue
            if filters.get("uri") is not None and row.uri != filters["uri"]:
                continue
            tags = filters.get("tags")
            if tags is not None:
                req = {tags} if isinstance(tags, str) else set(tags)
                if not req.issubset(set(row.tags)):
                    continue
            ids.append(row.id)
        return ids

    async def query_relationships(
        self,
        *,
        source_id: Optional[str] = None,
        target_id: Optional[str] = None,
        relationship_type: Optional[str] = None,
    ) -> List[ArtifactRelationship]:
        out = []
        for rel in self.relationships.values():
            if source_id is not None and rel.source_id != source_id:
                continue
            if target_id is not None and rel.target_id != target_id:
                continue
            if relationship_type is not None and rel.relationship_type != relationship_type:
                continue
            out.append(rel)
        return out

    async def get_metadata_bulk(
        self,
        artifact_ids: Sequence[str],
        keys: Optional[Sequence[str]] = None,
    ) -> Dict[str, Dict[str, MetadataValue]]:
        result: Dict[str, Dict[str, MetadataValue]] = {aid: {} for aid in artifact_ids}
        ids_set = set(artifact_ids)
        for (aid, k), (v, _tag) in self.metadata.items():
            if aid not in ids_set:
                continue
            if keys is not None and k not in keys:
                continue
            result[aid][k] = v
        return result

    async def query_journal_entries(
        self,
        *,
        artifact_id: Optional[str] = None,
        entry_type: Optional[str] = None,
        before=None,
        after=None,
    ) -> List[JournalEntry]:
        out = []
        for e in self.journal:
            if artifact_id is not None and e.artifact_id != artifact_id:
                continue
            if entry_type is not None and e.entry_type != entry_type:
                continue
            if before is not None and e.timestamp is not None and e.timestamp > before:
                continue
            if after is not None and e.timestamp is not None and e.timestamp < after:
                continue
            out.append(e)
        return out

    async def commit(self, payload: CommitPayload) -> str:
        self.commit_calls += 1
        for row in payload.artifact_creates:
            self.artifacts[row.id] = copy.deepcopy(row)
        for upd in payload.artifact_field_updates:
            row = self.artifacts.get(upd.id)
            if row is None:
                continue
            for k, v in upd.fields.items():
                setattr(row, k, v)
        for rel in payload.relationship_adds:
            key = (rel.source_id, rel.target_id, rel.relationship_type)
            self.relationships[key] = ArtifactRelationship(
                source_id=rel.source_id,
                target_id=rel.target_id,
                relationship_type=rel.relationship_type,
                metadata=dict(rel.metadata) if rel.metadata else None,
                created_at=datetime.utcnow(),
            )
        for key in payload.relationship_deletes:
            self.relationships.pop(key, None)
        for aid, k, v in payload.metadata_sets:
            # store with synthetic type tag for round-trip parity
            self.metadata[(aid, k)] = (v, _type_tag(v))
        for aid, k in payload.metadata_deletes:
            self.metadata.pop((aid, k), None)
        for entry in payload.journal_entries:
            self.journal.append(JournalEntry(
                artifact_id=entry.artifact_id,
                content=entry.content,
                entry_type=entry.entry_type,
                timestamp=datetime.utcnow(),
            ))
        return uuid.uuid4().hex

    async def soft_delete_artifacts(self, ids: Sequence[str]) -> None:
        for aid in ids:
            row = self.artifacts.get(aid)
            if row is not None:
                row.is_deleted = True
                row.deleted_at = datetime.utcnow()

    async def hard_delete_artifacts(self, ids: Sequence[str]) -> None:
        for aid in ids:
            self.artifacts.pop(aid, None)
            self.metadata = {
                k: v for k, v in self.metadata.items() if k[0] != aid
            }
            self.relationships = {
                k: v for k, v in self.relationships.items()
                if v.source_id != aid and v.target_id != aid
            }
            self.journal = [e for e in self.journal if e.artifact_id != aid]

    async def restore_artifacts(self, ids: Sequence[str]) -> None:
        for aid in ids:
            row = self.artifacts.get(aid)
            if row is not None:
                row.is_deleted = False
                row.deleted_at = None


def _type_tag(v: MetadataValue) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, int):
        return "int"
    if isinstance(v, float):
        return "float"
    return "str"
