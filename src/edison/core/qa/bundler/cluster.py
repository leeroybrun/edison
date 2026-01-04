from __future__ import annotations

from pathlib import Path
from typing import Optional

from edison.core.task.index import TaskIndex
from edison.core.task.relationships.codec import decode_frontmatter_relationships
from edison.core.utils.paths import PathResolver

from .scopes import BundleScope, ClusterSelection, parse_bundle_scope


def _bundle_root_for_task(task_id: str, *, project_root: Path) -> Optional[str]:
    """Return the bundle_root target for a task, if present."""
    index = TaskIndex(project_root=project_root)
    for _path, fm in index.scan_all_task_files(include_session_tasks=True):
        tid = str(fm.get("id") or "").strip() or None
        if tid != task_id:
            continue
        _rels, derived = decode_frontmatter_relationships(fm)
        root = str(derived.get("bundle_root") or "").strip()
        return root or None
    return None


def _bundle_members(root_task_id: str, *, project_root: Path) -> list[str]:
    """Return all tasks whose bundle_root targets `root_task_id` (excluding root)."""
    index = TaskIndex(project_root=project_root)
    members: list[str] = []
    for _path, fm in index.scan_all_task_files(include_session_tasks=True):
        tid = str(fm.get("id") or "").strip()
        if not tid or tid == root_task_id:
            continue
        _rels, derived = decode_frontmatter_relationships(fm)
        root = str(derived.get("bundle_root") or "").strip()
        if root == root_task_id:
            members.append(tid)
    return sorted(set(members))


def _hierarchy_descendants(root_task_id: str, *, project_root: Path) -> list[str]:
    index = TaskIndex(project_root=project_root)
    graph = index.get_task_graph(session_id=None, include_session_tasks=True)
    descendants = sorted(graph.get_all_descendants(root_task_id))
    return descendants


def select_cluster(
    task_id: str,
    *,
    scope: Optional[str] = None,
    project_root: Optional[Path] = None,
) -> ClusterSelection:
    """Select a cluster for QA bundling/validation.

    Semantics:
    - `hierarchy`: root is the provided task id
    - `bundle`: root is `task.bundle_root` when present, else the provided task id
    - `auto`: prefer `bundle` when root has any bundle members; else `hierarchy` if root has descendants; else single
    """
    project_root = project_root or PathResolver.resolve_project_root()
    # Default scope is configuration-driven, but CLI callers can override explicitly.
    effective_scope = scope
    if not str(effective_scope or "").strip():
        try:
            from edison.core.config.domains.qa import QAConfig

            validation_cfg = QAConfig(repo_root=project_root).get_validation_config()
            bundles_cfg = validation_cfg.get("bundles", {}) if isinstance(validation_cfg, dict) else {}
            if isinstance(bundles_cfg, dict):
                configured = str(bundles_cfg.get("defaultScope") or "").strip()
                if configured:
                    effective_scope = configured
        except Exception:
            effective_scope = scope

    requested = parse_bundle_scope(effective_scope)

    if requested == BundleScope.HIERARCHY:
        root = str(task_id)
        ids = (root, *_hierarchy_descendants(root, project_root=project_root))
        return ClusterSelection(root_task_id=root, scope=BundleScope.HIERARCHY, task_ids=tuple(ids))

    if requested == BundleScope.BUNDLE:
        bundle_root = _bundle_root_for_task(str(task_id), project_root=project_root)
        root = bundle_root or str(task_id)
        members = _bundle_members(root, project_root=project_root)
        return ClusterSelection(
            root_task_id=root,
            scope=BundleScope.BUNDLE,
            task_ids=tuple([root, *members]),
        )

    # AUTO
    root = str(task_id)
    members = _bundle_members(root, project_root=project_root)
    if members:
        return ClusterSelection(
            root_task_id=root,
            scope=BundleScope.BUNDLE,
            task_ids=tuple([root, *members]),
        )

    descendants = _hierarchy_descendants(root, project_root=project_root)
    if descendants:
        return ClusterSelection(
            root_task_id=root,
            scope=BundleScope.HIERARCHY,
            task_ids=tuple([root, *descendants]),
        )

    return ClusterSelection(root_task_id=root, scope=BundleScope.HIERARCHY, task_ids=(root,))


__all__ = [
    "BundleScope",
    "ClusterSelection",
    "select_cluster",
]
