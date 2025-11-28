"""Utility functions for session next computation.

Pure utility functions for task management and file operations.
No external dependencies on session state.
"""
from __future__ import annotations

import difflib
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

from edison.core.utils.paths import get_project_config_dir
from edison.core.utils.git import get_repo_root
from edison.core.utils.paths import get_management_paths
from edison.core.task.paths import get_root
from edison.core.task import TaskRepository


def project_cfg_dir() -> Path:
    """Get the project config directory."""
    return get_project_config_dir(get_repo_root())


def slugify(s: str) -> str:
    """Convert string to slug format."""
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "follow-up"


def stem_to_slug(stem: str) -> str:
    """Extract slug from task stem.

    Args:
        stem: Task file stem (e.g., "201-wave2-my-feature" or "201.1-wave2-fix")

    Returns:
        The slug portion (e.g., "my-feature" or "fix")
    """
    parts = stem.split("-", 2)
    if len(parts) >= 3:
        return parts[2]
    return stem


def all_task_files() -> List[Path]:
    """Get all task files across all states."""
    mgmt_paths = get_management_paths(get_root())
    root = mgmt_paths.get_tasks_root()
    files: List[Path] = []
    for st in ["todo", "wip", "blocked", "done", "validated"]:
        d = root / st
        if d.exists():
            files.extend(sorted(d.glob("*.md")))
    return files


def similar_tasks(title: str, *, top: int = 3, threshold: float = 0.6) -> List[Dict[str, Any]]:
    """Return up to 'top' similar existing tasks by slug similarity with scores."""
    want = slugify(title)
    candidates: List[Tuple[str, float]] = []
    for f in all_task_files():
        cand_id = f.stem
        cand_slug = stem_to_slug(cand_id)
        score = difflib.SequenceMatcher(None, want, cand_slug).ratio()
        if score >= threshold:
            candidates.append((cand_id, score))
    candidates.sort(key=lambda x: x[1], reverse=True)
    out: List[Dict[str, Any]] = []
    for cid, sc in candidates[:top]:
        out.append({"taskId": cid, "score": round(sc, 2)})
    return out


def extract_wave_and_base_id(task_id: str) -> tuple[str, str]:
    """Return (wave, baseId) from a task filename, defaulting sensibly."""
    try:
        task_repo = TaskRepository()
        p = task_repo.get_path(task_id)
        name = p.name  # e.g., 150-wave1-foo.md or 201.2-wave2-bar.md
        base = name.split("-", 1)[0]  # e.g., 150 or 201.2
        wave = name.split("-", 2)[1]  # e.g., wave1
        return wave, base
    except Exception:
        return "wave1", task_id


def allocate_child_id(base_id: str) -> str:
    """Find the next available base_id.N by scanning .project/tasks across states."""
    mgmt_paths = get_management_paths(get_root())
    root = mgmt_paths.get_tasks_root()
    states = ["todo","wip","blocked","done","validated"]
    existing = set()
    for st in states:
        d = root / st
        if d.exists():
            for f in d.glob("*.md"):
                tid = f.name.split("-",1)[0]
                if tid.startswith(base_id + "."):
                    existing.add(tid)
    # next N starting at 1
    n = 1
    while True:
        cand = f"{base_id}.{n}"
        if cand not in existing:
            return cand
        n += 1
