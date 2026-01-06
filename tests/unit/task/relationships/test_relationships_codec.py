from __future__ import annotations

from edison.core.task.relationships.codec import decode_frontmatter_relationships


def test_decode_frontmatter_relationships_ignores_legacy_relationship_keys() -> None:
    """Legacy relationship keys are no longer supported; only `relationships:` is canonical."""
    frontmatter = {
        "parent_id": "PARENT",
        "child_ids": ["CHILD"],
        "depends_on": ["DEP"],
        "blocks_tasks": ["BLOCKED"],
        "related": ["REL"],
        "bundle_root": "BUNDLE",
    }

    edges, derived = decode_frontmatter_relationships(frontmatter)

    assert edges == []
    assert derived["parent_id"] is None
    assert derived["child_ids"] == []
    assert derived["depends_on"] == []
    assert derived["blocks_tasks"] == []
    assert derived["related"] == []
    assert derived["bundle_root"] is None


def test_decode_frontmatter_relationships_parses_canonical_edges() -> None:
    frontmatter = {
        "relationships": [
            {"type": "parent", "target": "PARENT"},
            {"type": "child", "target": "CHILD"},
            {"type": "depends_on", "target": "DEP"},
            {"type": "blocks", "target": "BLOCKED"},
            {"type": "related", "target": "REL"},
            {"type": "bundle_root", "target": "BUNDLE"},
        ]
    }

    edges, derived = decode_frontmatter_relationships(frontmatter)

    assert {tuple(sorted(e.items())) for e in edges} == {
        tuple(sorted({"type": "parent", "target": "PARENT"}.items())),
        tuple(sorted({"type": "child", "target": "CHILD"}.items())),
        tuple(sorted({"type": "depends_on", "target": "DEP"}.items())),
        tuple(sorted({"type": "blocks", "target": "BLOCKED"}.items())),
        tuple(sorted({"type": "related", "target": "REL"}.items())),
        tuple(sorted({"type": "bundle_root", "target": "BUNDLE"}.items())),
    }
    assert derived["parent_id"] == "PARENT"
    assert derived["child_ids"] == ["CHILD"]
    assert derived["depends_on"] == ["DEP"]
    assert derived["blocks_tasks"] == ["BLOCKED"]
    assert derived["related"] == ["REL"]
    assert derived["bundle_root"] == "BUNDLE"

