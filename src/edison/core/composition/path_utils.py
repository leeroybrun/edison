"""Helpers for resolving project directory placeholders in composed content."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional

_PROJECT_DIR_PATTERN = re.compile(r"\{\{\s*PROJECT_EDISON_DIR\s*\}\}")


def _is_relative_to(path: Path, other: Path) -> bool:
    """Backport of Path.is_relative_to for Python 3.9 compatibility."""
    try:
        path.relative_to(other)
        return True
    except ValueError:
        return False


def _project_dir_replacement(
    project_dir: Path,
    target_path: Optional[Path],
    repo_root: Optional[Path],
) -> str:
    """Compute replacement string for {{PROJECT_EDISON_DIR}} tokens."""
    project_dir = project_dir.resolve()

    if target_path is not None:
        target_parent = target_path.resolve().parent
        if _is_relative_to(target_parent, project_dir):
            rel = Path(os.path.relpath(project_dir, target_parent))
            rel_str = rel.as_posix()
            return "." if rel_str == "." else rel_str

    if repo_root is not None:
        try:
            return project_dir.relative_to(repo_root.resolve()).as_posix()
        except ValueError:
            pass

    return project_dir.as_posix()


def resolve_project_dir_placeholders(
    text: str,
    *,
    project_dir: Path,
    target_path: Optional[Path] = None,
    repo_root: Optional[Path] = None,
) -> str:
    """Replace {{PROJECT_EDISON_DIR}} tokens with the configured project directory.

    When a target_path inside the project directory is provided, the replacement
    uses a relative path from the target to keep generated artifacts portable.
    """
    if not _PROJECT_DIR_PATTERN.search(text):
        return text

    replacement = _project_dir_replacement(project_dir, target_path, repo_root)
    return _PROJECT_DIR_PATTERN.sub(replacement, text)


__all__ = ["resolve_project_dir_placeholders"]
