from __future__ import annotations

from typing import Any, Dict

from edison.core.task.relationships.codec import normalize_relationships
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


def _edge(edge_type: str, target: str) -> dict[str, str]:
    return {"type": str(edge_type).strip(), "target": str(target).strip()}


def _edges_from_frontmatter_for_migration(frontmatter: Dict[str, Any]) -> list[dict[str, str]]:
    """Compute canonical edges for migration.

    - Prefers canonical `relationships:` when present.
    - Otherwise converts legacy relationship keys to canonical edges.
    """
    fm = frontmatter or {}
    raw_rel = fm.get("relationships")
    edges: list[dict[str, str]] = []

    if isinstance(raw_rel, list) and raw_rel:
        for item in raw_rel:
            if not isinstance(item, dict):
                continue
            edges.append(_edge(str(item.get("type") or ""), str(item.get("target") or "")))
        return normalize_relationships(edges)

    parent_id = str(fm.get("parent_id") or "").strip()
    if parent_id:
        edges.append(_edge("parent", parent_id))

    for cid in (fm.get("child_ids") or []):
        c = str(cid or "").strip()
        if c:
            edges.append(_edge("child", c))

    for dep in (fm.get("depends_on") or []):
        d = str(dep or "").strip()
        if d:
            edges.append(_edge("depends_on", d))

    for blk in (fm.get("blocks_tasks") or []):
        b = str(blk or "").strip()
        if b:
            edges.append(_edge("blocks", b))

    for rel in (fm.get("related") or fm.get("related_tasks") or []):
        r = str(rel or "").strip()
        if r:
            edges.append(_edge("related", r))

    bundle_root = str(fm.get("bundle_root") or "").strip()
    if bundle_root:
        edges.append(_edge("bundle_root", bundle_root))

    return normalize_relationships(edges)


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
    if not any(k in fm for k in _LEGACY_RELATIONSHIP_KEYS):
        return markdown

    edges = _edges_from_frontmatter_for_migration(fm)

    # Preserve original key ordering (PyYAML preserves insertion order for mappings).
    new_frontmatter: Dict[str, Any] = {}
    for key, value in fm.items():
        if key in _LEGACY_RELATIONSHIP_KEYS or key == "relationships":
            continue
        new_frontmatter[key] = value

    if edges:
        new_frontmatter["relationships"] = edges

    return format_frontmatter(new_frontmatter, exclude_none=True) + (doc.content or "")
