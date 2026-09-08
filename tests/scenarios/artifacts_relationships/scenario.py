from __future__ import annotations

from odyss_ai_flows_artifacts import (
    REL_DERIVED_FROM,
    REL_REFERS_TO,
    REL_SUMMARY_OF,
    ArtifactManager,
    JournalFilter,
    RelFilter,
)

from tests.artifact_helpers import InMemoryBackend


async def run_scenario():
    backend = InMemoryBackend()
    manager = ArtifactManager(backend=backend)

    parent = await manager.create_artifact(alias="parent")
    child = await parent.create_derived_artifact(alias="child")
    summary = await manager.create_artifact(alias="summary")
    sibling = await manager.create_artifact(alias="sibling")

    await manager.add_relationship(
        summary.id, parent.id, REL_SUMMARY_OF,
        metadata={"confidence": 0.82, "method": "semantic_similarity"},
    )
    await manager.add_relationship(
        sibling.id, child.id, REL_REFERS_TO,
    )
    await manager.commit()

    # Convenience helpers — derived_from direction (child --derived_from--> parent)
    parents_of_child = await manager.parent_relationships(child.id)
    assert {r.to_id for r in parents_of_child} == {parent.id}

    children_of_parent = await manager.child_relationships(parent.id)
    assert {r.from_id for r in children_of_parent} == {child.id}

    # Resolved-artifact convenience helpers
    assert {a.id for a in await child.parent_artifacts()} == {parent.id}
    assert {a.id for a in await parent.child_artifacts()} == {child.id}

    # Arbitrary named relationship + metadata round-trip
    summary_rels = await manager.query_relationships(
        relationship_type=REL_SUMMARY_OF, include_staged=False,
    )
    assert len(summary_rels) == 1
    assert summary_rels[0].metadata == {
        "confidence": 0.82, "method": "semantic_similarity",
    }

    # Outgoing/incoming
    out = await manager.query_outgoing_relationships(sibling.id)
    assert {r.relationship_type for r in out} == {REL_REFERS_TO}

    # Edges pointing AT child: only sibling --refers_to--> child
    # (child's derived_from edge points OUT to parent, not in).
    incoming = await manager.query_incoming_relationships(child.id)
    types_in = {(r.from_id, r.relationship_type) for r in incoming}
    assert types_in == {(sibling.id, REL_REFERS_TO)}

    # Staged add visible before commit
    new_target = await manager.create_artifact(alias="new")
    await manager.add_relationship(parent.id, new_target.id, REL_REFERS_TO)
    staged = await manager.query_outgoing_relationships(
        parent.id, REL_REFERS_TO, include_staged=True,
    )
    assert {r.to_id for r in staged} == {new_target.id}
    no_staged = await manager.query_outgoing_relationships(
        parent.id, REL_REFERS_TO, include_staged=False,
    )
    assert no_staged == []

    # Staged delete shadows committed relationship
    await manager.delete_relationship(summary.id, parent.id, REL_SUMMARY_OF)
    after_del = await manager.query_relationships(
        relationship_type=REL_SUMMARY_OF, include_staged=True,
    )
    assert after_del == []

    # ------------------------------------------------------------------
    # query_artifact_ids — typed relationship + journal filters
    # ------------------------------------------------------------------
    # Roll back the staged add+delete so the next assertions see the
    # committed graph: child -derived_from-> parent,
    #                  summary -summary_of-> parent,
    #                  sibling -refers_to-> child.
    manager.rollback()

    # children_of → artifacts derived from parent (parent's children)
    derived = await manager.query_artifact_ids(children_of=[parent.id])
    assert derived == [child.id]

    # parents_of → artifacts that child is derived from (child's parents)
    has_parent = await manager.query_artifact_ids(parents_of=[child.id])
    assert has_parent == [parent.id]

    # related — outgoing edge via `to_id`
    refs_child = await manager.query_artifact_ids(
        related=[RelFilter(REL_REFERS_TO, to_id=child.id)],
    )
    assert refs_child == [sibling.id]

    # related — incoming edge via `from_id`
    summarized_by = await manager.query_artifact_ids(
        related=[RelFilter(REL_SUMMARY_OF, from_id=summary.id)],
    )
    assert summarized_by == [parent.id]

    # Journal filter — entry_type match
    await manager.add_journal_entry(child.id, "indexed", entry_type="ingest")
    await manager.commit()
    ingested = await manager.query_artifact_ids(
        journal=JournalFilter(entry_type="ingest"),
    )
    assert ingested == [child.id]

    # Combined: tag + children_of + journal
    await manager.set_metadata(child.id, "score", 0.9)  # unrelated; ensures no interference
    combined = await manager.query_artifact_ids(
        children_of=[parent.id],
        journal=JournalFilter(entry_type="ingest"),
    )
    assert combined == [child.id]
    manager.rollback()

    # RelFilter validates: exactly one of to_id/from_id
    try:
        RelFilter(REL_REFERS_TO)
    except ValueError:
        pass
    else:
        raise AssertionError("RelFilter should reject no direction")
    try:
        RelFilter(REL_REFERS_TO, to_id="x", from_id="y")
    except ValueError:
        pass
    else:
        raise AssertionError("RelFilter should reject both directions")

    return {"ok": True}
