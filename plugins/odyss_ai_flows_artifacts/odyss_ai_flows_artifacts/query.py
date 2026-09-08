from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class RelFilter:
    type: str
    to_id: Optional[str] = None
    from_id: Optional[str] = None

    def __post_init__(self) -> None:
        if (self.to_id is None) == (self.from_id is None):
            raise ValueError(
                "RelFilter requires exactly one of `to_id` or `from_id`"
            )


@dataclass(frozen=True)
class JournalFilter:
    entry_type: Optional[str] = None
    before: Optional[datetime] = None
    after: Optional[datetime] = None


@dataclass
class ArtifactQuery:
    """Bundle of artifact filter criteria for the manager query methods."""

    alias: Optional[str] = None
    origin_operation_id: Optional[str] = None
    adapter_name: Optional[str] = None
    uri: Optional[str] = None
    tags: Optional[List[str]] = None
    children_of: Optional[List[str]] = None
    parents_of: Optional[List[str]] = None
    related: Optional[List[RelFilter]] = field(default=None)
    journal: Optional[JournalFilter] = None

    def to_filters(self) -> Dict[str, Any]:
        return {
            "alias": self.alias,
            "origin_operation_id": self.origin_operation_id,
            "adapter_name": self.adapter_name,
            "uri": self.uri,
            "tags": list(self.tags) if self.tags is not None else None,
            "children_of": list(self.children_of) if self.children_of else None,
            "parents_of": list(self.parents_of) if self.parents_of else None,
            "related": list(self.related) if self.related else None,
            "journal": self.journal,
        }
