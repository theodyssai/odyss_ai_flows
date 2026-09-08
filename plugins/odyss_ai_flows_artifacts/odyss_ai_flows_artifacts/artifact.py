from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional, Set

from odyss_ai_flows_artifacts.metadata import MetadataValue
from odyss_ai_flows_artifacts.relationship import (
    REL_DERIVED_FROM,
    ArtifactRelationship,
)

if TYPE_CHECKING:
    from odyss_ai_flows_artifacts.artifact_manager import ArtifactManager
    from odyss_ai_flows_artifacts.backends.base import ArtifactRow


class Artifact:
    def __init__(
        self,
        *,
        id: Optional[str] = None,
        alias: Optional[str] = None,
        adapter_name: Optional[str] = None,
        adapter: Any = None,
        uri: Optional[str] = None,
        origin_operation_id: Optional[str] = None,
        tags: Optional[Iterable[str]] = None,
        is_deleted: bool = False,
        manager: Optional["ArtifactManager"] = None,
    ):
        self.id = id or str(uuid.uuid4())
        self.alias = alias
        self.adapter_name = adapter_name
        self.adapter = adapter
        self.uri = uri
        self.origin_operation_id = origin_operation_id
        self.tags: Set[str] = set(tags) if tags else set()
        self.is_deleted = is_deleted
        self.metadata: Dict[str, MetadataValue] = {}
        self.data: Any = None
        self._manager = manager

    @classmethod
    def from_row(
        cls,
        row: "ArtifactRow",
        *,
        adapter: Any = None,
        manager: Optional["ArtifactManager"] = None,
    ) -> "Artifact":
        return cls(
            id=row.id,
            alias=row.alias,
            adapter_name=row.adapter_name,
            adapter=adapter,
            uri=row.uri,
            origin_operation_id=row.origin_operation_id,
            tags=row.tags,
            is_deleted=row.is_deleted,
            manager=manager,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "alias": self.alias,
            "adapter_name": self.adapter_name,
            "uri": self.uri,
            "origin_operation_id": self.origin_operation_id,
            "tags": sorted(self.tags),
            "is_deleted": self.is_deleted,
            "metadata": dict(self.metadata),
        }

    @property
    def dirty(self) -> bool:
        if self._manager is None:
            return False
        return self.id in self._manager._dirty_artifacts

    def __getitem__(self, key: str) -> MetadataValue:
        return self.metadata.get(key)

    def __getattr__(self, name: str):
        if name in ("adapter", "_manager"):
            raise AttributeError(name)
        adapter = self._resolve_adapter()
        if adapter is not None and hasattr(adapter, name):
            attr = getattr(adapter, name)
            if callable(attr):
                def wrapper(*args, **kwargs):
                    return attr(self, *args, **kwargs)
                return wrapper
            return attr
        raise AttributeError(
            f"{type(self).__name__!r} has no attribute {name!r}"
        )

    def _resolve_adapter(self) -> Any:
        if self.__dict__.get("adapter") is None:
            name = self.__dict__.get("adapter_name")
            manager = self.__dict__.get("_manager")
            registry = getattr(manager, "adapter_registry", None)
            if name and registry is not None:
                try:
                    self.adapter = registry.load(name)
                except LookupError:
                    self.adapter = None
        return self.__dict__.get("adapter")

    def _require_adapter(self, operation: str) -> Any:
        adapter = self._resolve_adapter()
        if adapter is None or not hasattr(adapter, operation):
            raise NotImplementedError(
                f"Adapter {self.adapter_name!r} for artifact {self.id} "
                f"does not implement {operation!r}."
            )
        return adapter

    async def read(self, *args, **kwargs):
        result = await self._require_adapter("read").read(self, *args, **kwargs)
        if result is not None:
            self.data = result
        return result

    async def write(self, *args, **kwargs):
        return await self._require_adapter("write").write(self, *args, **kwargs)

    async def delete(self, *args, **kwargs):
        result = await self._require_adapter("delete").delete(self, *args, **kwargs)
        self.data = None
        return result

    async def exists(self, *args, **kwargs):
        return await self._require_adapter("exists").exists(self, *args, **kwargs)

    def _require_manager(self) -> "ArtifactManager":
        if self._manager is None:
            raise RuntimeError(
                f"Artifact {self.id} has no attached manager; "
                f"cannot perform managed operation."
            )
        return self._manager

    async def set_metadata(self, key: str, value: MetadataValue) -> None:
        await self._require_manager().set_metadata(self.id, key, value)

    async def set_metadata_bulk(self, mapping: Dict[str, MetadataValue]) -> None:
        await self._require_manager().set_metadata_bulk(self.id, mapping)

    async def delete_metadata(self, key: str) -> None:
        await self._require_manager().delete_metadata(self.id, key)

    async def add_journal_entry(
        self,
        content: str,
        entry_type: Optional[str] = None,
    ) -> None:
        await self._require_manager().add_journal_entry(
            self.id, content, entry_type=entry_type,
        )

    async def create_derived_artifact(self, **kwargs) -> "Artifact":
        manager = self._require_manager()
        derived = await manager.create_artifact(**kwargs)
        # Edge follows the verb: derived --derived_from--> self (origin).
        await manager.add_relationship(
            derived.id, self.id, REL_DERIVED_FROM,
        )
        return derived

    async def add_relationship(
        self,
        target,
        relationship_type: str,
        metadata: Optional[Dict[str, MetadataValue]] = None,
    ) -> None:
        to_id = target.id if isinstance(target, Artifact) else target
        await self._require_manager().add_relationship(
            self.id, to_id, relationship_type, metadata=metadata,
        )

    async def parent_relationships(self) -> List[ArtifactRelationship]:
        # Parents = origins this artifact derives from = its outgoing
        # derived_from edges (this --derived_from--> parent).
        return await self._require_manager().query_outgoing_relationships(
            self.id, relationship_type=REL_DERIVED_FROM,
        )

    async def child_relationships(self) -> List[ArtifactRelationship]:
        # Children = artifacts derived from this = its incoming derived_from
        # edges (child --derived_from--> this).
        return await self._require_manager().query_incoming_relationships(
            self.id, relationship_type=REL_DERIVED_FROM,
        )

    async def parent_artifacts(self) -> List["Artifact"]:
        rels = await self.parent_relationships()
        return await self._require_manager().get_artifacts(
            [r.to_id for r in rels],
        )

    async def child_artifacts(self) -> List["Artifact"]:
        rels = await self.child_relationships()
        return await self._require_manager().get_artifacts(
            [r.from_id for r in rels],
        )
