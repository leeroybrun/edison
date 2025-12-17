"""Session next package - compute next actions for a session.

This package provides deterministic next action computation for session orchestration.

Public API:
    compute_next: Main function to compute recommended next actions
"""
from __future__ import annotations

from edison.core.session.next.compute import compute_next, main

def _all_task_files():
    """Backward-compat helper: list all task files (global + session-scoped)."""
    from pathlib import Path

    from edison.core.config.domains.workflow import WorkflowConfig
    from edison.core.utils.paths import PathResolver, get_management_paths

    project_root = PathResolver.resolve_project_root()
    mgmt = get_management_paths(project_root)
    root = mgmt.get_tasks_root()

    files: list[Path] = []
    for st in WorkflowConfig(repo_root=project_root).get_states("task"):
        d = root / st
        if d.exists():
            files.extend(sorted(d.glob("*.md")))
    return [p.resolve() for p in files]


__all__ = ["compute_next", "main", "_all_task_files"]
