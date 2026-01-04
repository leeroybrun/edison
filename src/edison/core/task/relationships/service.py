from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from edison.core.entity import PersistenceError
from edison.core.utils.paths import PathResolver

from edison.core.task.models import Task
from edison.core.task.repository import TaskRepository

from .codec import encode_task_relationships, normalize_relationships


RelationshipEdge = Dict[str, str]


_INVERSE: dict[str, str] = {
    "parent": "child",
    "child": "parent",
    "depends_on": "blocks",
    "blocks": "depends_on",
    "related": "related",
}


def _edge(edge_type: str, target: str) -> RelationshipEdge:
    return {"type": str(edge_type).strip(), "target": str(target).strip()}


def _derived_fields(edges: List[RelationshipEdge]) -> dict[str, Any]:
    return {
        "parent_id": next((e["target"] for e in edges if e.get("type") == "parent"), None),
        "child_ids": [e["target"] for e in edges if e.get("type") == "child"],
        "depends_on": [e["target"] for e in edges if e.get("type") == "depends_on"],
        "blocks_tasks": [e["target"] for e in edges if e.get("type") == "blocks"],
        "related": [e["target"] for e in edges if e.get("type") == "related"],
        "bundle_root": next((e["target"] for e in edges if e.get("type") == "bundle_root"), None),
    }


def _apply_edges_to_task(task: Task, edges: List[RelationshipEdge]) -> None:
    task.relationships = list(edges)
    derived = _derived_fields(edges)
    task.parent_id = derived["parent_id"]
    task.child_ids = list(derived["child_ids"])
    task.depends_on = list(derived["depends_on"])
    task.blocks_tasks = list(derived["blocks_tasks"])
    task.related = list(derived["related"])
    # bundle_root is not yet a first-class Task field; preserve via relationships only.


def _remove_edges(edges: List[RelationshipEdge], edge_type: str, targets: set[str] | None = None) -> List[RelationshipEdge]:
    t = str(edge_type).strip()
    keep: List[RelationshipEdge] = []
    for e in edges:
        if str(e.get("type") or "").strip() != t:
            keep.append(e)
            continue
        if targets is None:
            continue
        if str(e.get("target") or "").strip() in targets:
            continue
        keep.append(e)
    return keep


class TaskRelationshipService:
    """Task relationship mutator service (single source of truth).

    This service is responsible for enforcing relationship invariants and
    performing any required cross-task mutations (inverse/symmetric edges).
    """

    def __init__(self, *, project_root: Optional[Path] = None) -> None:
        self.project_root = project_root or PathResolver.resolve_project_root()
        self.repo = TaskRepository(project_root=self.project_root)

    def add(
        self,
        *,
        task_id: str,
        rel_type: str,
        target_id: str,
        force: bool = False,
    ) -> None:
        a_id = str(task_id).strip()
        b_id = str(target_id).strip()
        t = str(rel_type).strip()
        if not a_id or not b_id or not t:
            raise PersistenceError("add relationship requires task_id, rel_type, target_id")
        if a_id == b_id:
            raise PersistenceError("Cannot add relationship to self")

        a = self.repo.get(a_id)
        b = self.repo.get(b_id)
        if not a:
            raise PersistenceError(f"Task not found: {a_id}")
        if not b:
            raise PersistenceError(f"Task not found: {b_id}")

        a_edges = encode_task_relationships(a)
        b_edges = encode_task_relationships(b)

        # Directed-only relationship: bundle_root (no inverse).
        if t == "bundle_root":
            existing = [e for e in a_edges if e.get("type") == "bundle_root"]
            if existing and str(existing[0].get("target") or "").strip() != b_id:
                if not force:
                    raise PersistenceError("Task already has a bundle_root; use force to replace")
                a_edges = _remove_edges(a_edges, "bundle_root")
            a_edges.append(_edge("bundle_root", b_id))
            a_edges = normalize_relationships(a_edges)
            _apply_edges_to_task(a, a_edges)
            self.repo.save(a)
            return

        inv = _INVERSE.get(t)
        if not inv:
            raise PersistenceError(f"Unknown relationship type: {t}")

        # Parent/child single-parent enforcement (fail-closed unless force).
        if t in {"parent", "child"}:
            # Determine which side is the child (the one that must have a single parent edge).
            child_task = a if t == "parent" else b
            child_edges = a_edges if t == "parent" else b_edges
            existing_parent = next((e for e in child_edges if e.get("type") == "parent"), None)
            desired_parent = b_id if t == "parent" else a_id
            if existing_parent and str(existing_parent.get("target") or "").strip() != desired_parent:
                if not force:
                    raise PersistenceError(
                        f"Task {child_task.id} already has parent {existing_parent.get('target')}; "
                        "single-parent is enforced"
                    )

                # Force: remove old parent edge and corresponding child edge on old parent task.
                old_parent_id = str(existing_parent.get("target") or "").strip()
                child_edges = _remove_edges(child_edges, "parent")
                if t == "parent":
                    a_edges = child_edges
                else:
                    b_edges = child_edges

                old_parent = self.repo.get(old_parent_id)
                if old_parent:
                    old_edges = encode_task_relationships(old_parent)
                    old_edges = _remove_edges(old_edges, "child", targets={child_task.id})
                    old_edges = normalize_relationships(old_edges)
                    _apply_edges_to_task(old_parent, old_edges)
                    self.repo.save(old_parent)

        # Symmetric/self-inverse (related) vs inverse mapping.
        a_edges.append(_edge(t, b_id))
        if t == "related":
            b_edges.append(_edge("related", a_id))
        else:
            b_edges.append(_edge(inv, a_id))

        a_edges = normalize_relationships(a_edges)
        b_edges = normalize_relationships(b_edges)

        _apply_edges_to_task(a, a_edges)
        _apply_edges_to_task(b, b_edges)

        self.repo.save(a)
        self.repo.save(b)

    def remove(
        self,
        *,
        task_id: str,
        rel_type: str,
        target_id: str,
    ) -> None:
        a_id = str(task_id).strip()
        b_id = str(target_id).strip()
        t = str(rel_type).strip()
        if not a_id or not b_id or not t:
            raise PersistenceError("remove relationship requires task_id, rel_type, target_id")
        if a_id == b_id:
            raise PersistenceError("Cannot remove relationship to self")

        a = self.repo.get(a_id)
        b = self.repo.get(b_id)
        if not a:
            raise PersistenceError(f"Task not found: {a_id}")
        if not b:
            raise PersistenceError(f"Task not found: {b_id}")

        a_edges = encode_task_relationships(a)
        b_edges = encode_task_relationships(b)

        if t == "bundle_root":
            a_edges = _remove_edges(a_edges, "bundle_root", targets={b_id})
            a_edges = normalize_relationships(a_edges)
            _apply_edges_to_task(a, a_edges)
            self.repo.save(a)
            return

        inv = _INVERSE.get(t)
        if not inv:
            raise PersistenceError(f"Unknown relationship type: {t}")

        a_edges = _remove_edges(a_edges, t, targets={b_id})
        if t == "related":
            b_edges = _remove_edges(b_edges, "related", targets={a_id})
        else:
            b_edges = _remove_edges(b_edges, inv, targets={a_id})

        a_edges = normalize_relationships(a_edges)
        b_edges = normalize_relationships(b_edges)

        _apply_edges_to_task(a, a_edges)
        _apply_edges_to_task(b, b_edges)

        self.repo.save(a)
        self.repo.save(b)
