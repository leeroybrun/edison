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
    """Decode canonical relationships from task frontmatter.

    Legacy relationship keys are intentionally not supported. Task relationship
    information must be expressed via canonical `relationships:` edges.

    Returns (relationships, derived_relationship_fields) where derived fields include:
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

    if isinstance(raw_rel, list) and raw_rel:
        for item in raw_rel:
            if not isinstance(item, dict):
                continue
            edges.append(_edge(str(item.get("type") or ""), str(item.get("target") or "")))

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
