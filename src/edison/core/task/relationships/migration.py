from __future__ import annotations

from typing import Any, Dict

from edison.core.task.relationships.codec import decode_frontmatter_relationships
from edison.core.utils.text import format_frontmatter, has_frontmatter, parse_frontmatter


_LEGACY_RELATIONSHIP_KEYS = {
    "parent_id",
    "child_ids",
    "depends_on",
    "blocks_tasks",
    "related",
    "related_tasks",
    "bundle_root",
}


def migrate_task_markdown_relationships(markdown: str) -> str:
    """Migrate legacy relationship keys in task markdown to canonical `relationships:`.

    - Preserves non-relationship frontmatter keys and the markdown body.
    - Canonical `relationships:` takes precedence when present.
    - Removes legacy keys unconditionally.
    - Omits `relationships:` entirely when there are no edges.
    """
    if not markdown:
        return markdown
    if not has_frontmatter(markdown):
        return markdown

    doc = parse_frontmatter(markdown)
    fm: Dict[str, Any] = dict(doc.frontmatter or {})

    edges, _derived = decode_frontmatter_relationships(fm)

    # Preserve original key ordering (PyYAML preserves insertion order for mappings).
    new_frontmatter: Dict[str, Any] = {}
    for key, value in fm.items():
        if key in _LEGACY_RELATIONSHIP_KEYS or key == "relationships":
            continue
        new_frontmatter[key] = value

    if edges:
        new_frontmatter["relationships"] = edges

    return format_frontmatter(new_frontmatter, exclude_none=True) + (doc.content or "")
