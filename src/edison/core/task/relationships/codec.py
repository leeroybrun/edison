from __future__ import annotations

from typing import Any, Dict, List, Tuple

from edison.core.relationships.models import normalize_edges


RelationshipEdge = Dict[str, str]


def _edge(edge_type: str, target: str) -> RelationshipEdge:
    return {"type": str(edge_type).strip(), "target": str(target).strip()}


def normalize_relationships(edges: List[RelationshipEdge]) -> List[RelationshipEdge]:
    """Normalize relationships list deterministically.

    Invariants (fail-closed):
    - no self edges (must be filtered by caller when task id is known)
    - no duplicates
    - stable ordering: (type, target)
    - single-parent: at most one `parent` edge
    - single bundle root: at most one `bundle_root` edge
    """
    return normalize_edges(edges or [], singleton_types=("parent", "bundle_root"))


def decode_frontmatter_relationships(frontmatter: Dict[str, Any]) -> Tuple[List[RelationshipEdge], Dict[str, Any]]:
    """Decode canonical relationships (or legacy fields) from task frontmatter.

    Returns (relationships, derived_legacy_fields) where derived legacy fields include:
    - parent_id
    - child_ids
    - depends_on
    - blocks_tasks
    - related
    - bundle_root (string or None)
    """
    fm = frontmatter or {}
    raw_rel = fm.get("relationships")
    edges: List[RelationshipEdge] = []

    # Canonical relationships take precedence when present.
    if isinstance(raw_rel, list) and raw_rel:
        for item in raw_rel:
            if not isinstance(item, dict):
                continue
            edges.append(_edge(str(item.get("type") or ""), str(item.get("target") or "")))
    else:
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

    edges = normalize_relationships(edges)

    derived: Dict[str, Any] = {
        "parent_id": next((e["target"] for e in edges if e.get("type") == "parent"), None),
        "child_ids": [e["target"] for e in edges if e.get("type") == "child"],
        "depends_on": [e["target"] for e in edges if e.get("type") == "depends_on"],
        "blocks_tasks": [e["target"] for e in edges if e.get("type") == "blocks"],
        "related": [e["target"] for e in edges if e.get("type") == "related"],
        "bundle_root": next((e["target"] for e in edges if e.get("type") == "bundle_root"), None),
    }
    return edges, derived


def encode_task_relationships(task: Any) -> List[RelationshipEdge]:
    """Encode a task's relationships into canonical edges.

    Canonical `task.relationships` is the single source of truth. Legacy fields
    should not contribute edges, to avoid competing sources of truth.
    """
    edges: List[RelationshipEdge] = []

    for item in (getattr(task, "relationships", None) or []):
        if isinstance(item, dict):
            edges.append(_edge(str(item.get("type") or ""), str(item.get("target") or "")))

    return normalize_relationships(edges)
