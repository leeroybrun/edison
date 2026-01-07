"""Lock discovery helpers.

This module is intentionally generic and provides a single place to locate
Edison-managed lock files in a repo/worktree.
"""

from __future__ import annotations

from pathlib import Path

from edison.core.utils.paths import get_project_config_dir


def discover_project_lock_files(*, repo_root: Path) -> list[Path]:
    """Return Edison-managed lock files under the project config directory.

    This includes:
    - `<project-config>/_locks/**`
    - `<project-config>/session/*/_locks/**`
    """
    repo_root = Path(repo_root).resolve()
    cfg = get_project_config_dir(repo_root, create=False)

    out: list[Path] = []

    roots = [
        cfg / "_locks",
        cfg / "session",
    ]

    for root in roots:
        if not root.exists():
            continue
        if root.name == "session":
            # session/<session-id>/_locks/**/*
            for sid_dir in root.iterdir():
                locks_dir = sid_dir / "_locks"
                if not locks_dir.exists():
                    continue
                out.extend([p for p in locks_dir.rglob("*") if p.is_file()])
        else:
            out.extend([p for p in root.rglob("*") if p.is_file()])

    return sorted(set(out), key=lambda p: str(p))


__all__ = ["discover_project_lock_files"]

