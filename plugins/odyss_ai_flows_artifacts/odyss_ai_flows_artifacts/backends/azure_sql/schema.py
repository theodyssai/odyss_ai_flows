from typing import Any, Dict, List, Optional, Sequence


_ALLOWED_INDEX_TABLES = {
    "artifacts",
    "artifact_tags",
    "artifact_relationships",
    "artifact_metadata",
    "artifact_journal",
}
_ALLOWED_INDEX_COLUMNS = {
    "artifacts": {
        "id", "alias", "adapter_name", "uri",
        "origin_operation_id", "is_deleted", "deleted_at",
    },
    "artifact_tags": {
        "artifact_id", "tag",
    },
    "artifact_relationships": {
        "from_id", "to_id", "relationship_type", "created_at",
    },
    "artifact_metadata": {
        "artifact_id", "meta_key", "meta_value", "meta_type",
    },
    "artifact_journal": {
        "artifact_id", "timestamp", "entry_type",
    },
}

# CREATE TABLE templates keyed by logical table name. `{table}` is filled with
# the schema-qualified name at build time.
_TABLE_DDL = {
    "artifacts": """
        IF OBJECT_ID('{table}', 'U') IS NULL
        CREATE TABLE {table} (
            id NVARCHAR(255) PRIMARY KEY,
            alias NVARCHAR(255) NULL,
            adapter_name NVARCHAR(255) NULL,
            uri NVARCHAR(1024) NULL,
            origin_operation_id NVARCHAR(255) NULL,
            is_deleted BIT NOT NULL DEFAULT 0,
            deleted_at DATETIME2 NULL
        )
    """,
    "artifact_tags": """
        IF OBJECT_ID('{table}', 'U') IS NULL
        CREATE TABLE {table} (
            artifact_id NVARCHAR(255) NOT NULL,
            tag NVARCHAR(255) NOT NULL,
            PRIMARY KEY (artifact_id, tag)
        )
    """,
    "artifact_relationships": """
        IF OBJECT_ID('{table}', 'U') IS NULL
        CREATE TABLE {table} (
            from_id NVARCHAR(255) NOT NULL,
            to_id NVARCHAR(255) NOT NULL,
            relationship_type NVARCHAR(255) NOT NULL,
            metadata_json NVARCHAR(MAX) NULL CHECK (metadata_json IS NULL OR ISJSON(metadata_json) = 1),
            created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
            PRIMARY KEY (from_id, to_id, relationship_type)
        )
    """,
    "artifact_metadata": """
        IF OBJECT_ID('{table}', 'U') IS NULL
        CREATE TABLE {table} (
            artifact_id NVARCHAR(255) NOT NULL,
            meta_key NVARCHAR(255) NOT NULL,
            meta_value NVARCHAR(MAX) NULL,
            meta_type NVARCHAR(8) NOT NULL,
            PRIMARY KEY (artifact_id, meta_key)
        )
    """,
    "artifact_journal": """
        IF OBJECT_ID('{table}', 'U') IS NULL
        CREATE TABLE {table} (
            artifact_id NVARCHAR(255) NOT NULL,
            timestamp DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
            entry_type NVARCHAR(255) NULL,
            content NVARCHAR(MAX) NULL
        )
    """,
}

# Default indexes as (name, table, columns) tuples.
_DEFAULT_INDEXES = [
    ("ix_artifacts_alias", "artifacts", ["alias"]),
    ("ix_artifacts_adapter", "artifacts", ["adapter_name"]),
    ("ix_artifacts_origin_op", "artifacts", ["origin_operation_id"]),
    ("ix_tags_tag", "artifact_tags", ["tag", "artifact_id"]),
    ("ix_rel_from_type", "artifact_relationships",
     ["from_id", "relationship_type"]),
    ("ix_rel_to_type", "artifact_relationships",
     ["to_id", "relationship_type"]),
    # meta_value is NVARCHAR(MAX), so it can't be an index KEY column on SQL
    # Server; carry it as a covering INCLUDE column instead. Nothing seeks on
    # meta_value (only meta_key/artifact_id are filtered), so this preserves the
    # index's purpose (fast meta_key lookups that also read the value).
    ("ix_meta_key_value", "artifact_metadata", ["meta_key"], ["meta_value"]),
    ("ix_journal_artifact_ts", "artifact_journal",
     ["artifact_id", "timestamp"]),
    ("ix_journal_type_ts", "artifact_journal", ["entry_type", "timestamp"]),
]


def safe_ident(name: str) -> str:
    if not name.replace("_", "").isalnum():
        raise ValueError(f"Unsafe identifier: {name!r}")
    return name


def qualify(schema: Optional[str], table: str) -> str:
    return f"{schema}.{table}" if schema else table


def _create_index(
    schema: Optional[str], name: str, table: str, columns: Sequence[str],
    include: Optional[Sequence[str]] = None,
) -> str:
    cols = ", ".join(safe_ident(c) for c in columns)
    qualified = qualify(schema, table)
    # INCLUDE (covering) columns may be LOB/MAX types, which are illegal as
    # index KEY columns on SQL Server (error 1919). Keep large values here.
    include_clause = ""
    if include:
        inc = ", ".join(safe_ident(c) for c in include)
        include_clause = f" INCLUDE ({inc})"
    return (
        f"IF NOT EXISTS (SELECT 1 FROM sys.indexes "
        f"WHERE name = '{name}' AND object_id = OBJECT_ID('{qualified}')) "
        f"CREATE INDEX {name} ON {qualified} ({cols}){include_clause}"
    )


def _extra_index_statements(
    schema: Optional[str], extra_indexes: Sequence[Dict[str, Any]],
) -> List[str]:
    out = []
    for spec in extra_indexes:
        name = safe_ident(spec["name"])
        table = spec["table"]
        cols = list(spec["columns"])
        if table not in _ALLOWED_INDEX_TABLES:
            raise ValueError(f"Unknown table for extra index: {table!r}")
        allowed = _ALLOWED_INDEX_COLUMNS[table]
        for c in cols:
            if c not in allowed:
                raise ValueError(
                    f"Column {c!r} not allowed for table {table!r}"
                )
        out.append(_create_index(schema, name, table, cols))
    return out


def schema_statements(
    schema: Optional[str] = None,
    extra_indexes: Optional[Sequence[Dict[str, Any]]] = None,
) -> List[str]:
    """Full ordered DDL: create tables, then default and extra indexes."""
    stmts = [
        ddl.format(table=qualify(schema, table))
        for table, ddl in _TABLE_DDL.items()
    ]
    stmts.extend(
        _create_index(
            schema, entry[0], entry[1], entry[2],
            entry[3] if len(entry) > 3 else None,
        )
        for entry in _DEFAULT_INDEXES
    )
    stmts.extend(_extra_index_statements(schema, extra_indexes or []))
    return stmts
