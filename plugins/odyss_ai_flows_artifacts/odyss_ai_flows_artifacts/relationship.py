from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional

from odyss_ai_flows_artifacts.metadata import MetadataValue


REL_DERIVED_FROM = "derived_from"
REL_SUMMARY_OF = "summary_of"
REL_CHUNK_OF = "chunk_of"
REL_REFERS_TO = "refers_to"
REL_EMBEDDING_OF = "embedding_of"
REL_EXPORTED_FROM = "exported_from"


@dataclass(frozen=True)
class ArtifactRelationship:
    # Edge reads "from_id {relationship_type} to_id" — e.g. for derived_from,
    # from_id is the derived (child) artifact and to_id is its origin (parent).
    from_id: str
    to_id: str
    relationship_type: str
    metadata: Optional[Dict[str, MetadataValue]] = None
    created_at: Optional[datetime] = None
