from dataclasses import dataclass, field
from datetime import datetime
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Protocol,
    Sequence,
    Tuple,
)

from odyss_ai_flows_artifacts.metadata import MetadataValue
from odyss_ai_flows_artifacts.relationship import ArtifactRelationship


@dataclass
class ArtifactRow:
    id: str
    alias: Optional[str] = None
    adapter_name: Optional[str] = None
    uri: Optional[str] = None
    origin_operation_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None


@dataclass
class ArtifactFieldUpdate:
    id: str
    fields: Dict[str, Any]


@dataclass
class JournalEntry:
    artifact_id: str
    content: str
    entry_type: Optional[str] = None
    timestamp: Optional[datetime] = None


@dataclass
class CommitPayload:
    artifact_creates: List[ArtifactRow] = field(default_factory=list)
    artifact_field_updates: List[ArtifactFieldUpdate] = field(default_factory=list)
    relationship_adds: List[ArtifactRelationship] = field(default_factory=list)
    relationship_deletes: List[Tuple[str, str, str]] = field(default_factory=list)
    metadata_sets: List[Tuple[str, str, MetadataValue]] = field(default_factory=list)
    metadata_deletes: List[Tuple[str, str]] = field(default_factory=list)
    journal_entries: List[JournalEntry] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not (
            self.artifact_creates
            or self.artifact_field_updates
            or self.relationship_adds
            or self.relationship_deletes
            or self.metadata_sets
            or self.metadata_deletes
            or self.journal_entries
        )


class Backend(Protocol):
    async def init_schema(self) -> None: ...
    async def close(self) -> None: ...

    def with_schema(self, schema: Optional[str]) -> "Backend":
        return self

    async def get_artifacts(
        self,
        ids: Sequence[str],
        *,
        include_deleted: bool = False,
    ) -> List[ArtifactRow]: ...

    async def query_artifact_ids(
        self,
        *,
        filters: Dict[str, Any],
        include_deleted: bool = False,
    ) -> List[str]: ...

    async def query_relationships(
        self,
        *,
        from_id: Optional[str] = None,
        to_id: Optional[str] = None,
        relationship_type: Optional[str] = None,
    ) -> List[ArtifactRelationship]: ...

    async def get_metadata_bulk(
        self,
        artifact_ids: Sequence[str],
        keys: Optional[Sequence[str]] = None,
    ) -> Dict[str, Dict[str, MetadataValue]]: ...

    async def query_journal_entries(
        self,
        *,
        artifact_id: Optional[str] = None,
        entry_type: Optional[str] = None,
        before: Optional[datetime] = None,
        after: Optional[datetime] = None,
    ) -> List[JournalEntry]: ...

    async def commit(self, payload: CommitPayload) -> str: ...

    async def soft_delete_artifacts(self, ids: Sequence[str]) -> None: ...
    async def hard_delete_artifacts(self, ids: Sequence[str]) -> None: ...
    async def restore_artifacts(self, ids: Sequence[str]) -> None: ...
