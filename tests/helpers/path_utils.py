"""Path resolution utilities for test helpers.

Consolidates path finding and resolution logic used across test helpers.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional
from tests.config import get_task_states, get_qa_states, get_session_states


def resolve_expected_path(path: Path) -> Path:
    """Resolve a possibly-global path to the actual location (session-aware).

    If the exact path exists, return it. Otherwise, search under
    .project/sessions/wip/*/{tasks,qa}/**/<basename> and return the first match.

    Args:
        path: Path to resolve (may be global or session-scoped)

    Returns:
        Resolved path (original if found, or session-scoped match)
    """
    if path.exists():
        return path
    # Only try to resolve for .project paths
    try:
        parts = list(path.parts)
        if ".project" not in parts:
            return path
        idx = parts.index(".project")
        root = Path(*parts[: idx + 1])
        # Load default session state from config (NO hardcoded values)
        from tests.config import get_default_value
        default_state = get_default_value("session", "state")
        sessions_root = root / "sessions" / default_state
        if not sessions_root.exists():
            return path
        domain = "tasks" if "/tasks/" in str(path) else ("qa" if "/qa/" in str(path) else None)
        if not domain:
            return path
        for candidate in sessions_root.glob(f"*/{domain}/**/{path.name}"):
            if candidate.is_file():
                return candidate
    except Exception:
        return path
    return path


def find_in_states(
    project_root: Path,
    record_id: str,
    domain: str,
    states: Optional[list[str]] = None,
    suffix: str = ""
) -> Optional[Path]:
    """Find a record file by ID across state directories.

    Args:
        project_root: Root .project directory
        record_id: Record ID to find
        domain: Domain name (tasks, qa, sessions)
        states: List of state directories to search (defaults to domain-specific)
        suffix: File suffix (e.g., "-qa.md", ".json")

    Returns:
        Path to record file, or None if not found
    """
    if states is None:
        # Load states from YAML config (NO hardcoded values)
        if domain == "tasks":
            states = get_task_states()
        elif domain == "qa":
            states = get_qa_states()
        elif domain == "sessions":
            states = get_session_states()
        else:
            states = []

    for state_dir in states:
        record_path = project_root / domain / state_dir / f"{record_id}{suffix}"
        if record_path.exists():
            return record_path
    return None


def get_record_state(
    project_root: Path,
    record_id: str,
    domain: str,
    states: Optional[list[str]] = None,
    suffix: str = ""
) -> Optional[str]:
    """Get current state of a record by finding its file.

    Args:
        project_root: Root .project directory
        record_id: Record ID to find
        domain: Domain name (tasks, qa, sessions)
        states: List of state directories to search
        suffix: File suffix (e.g., "-qa.md", ".json")

    Returns:
        State name or None if not found
    """
    record_path = find_in_states(project_root, record_id, domain, states, suffix)
    if record_path:
        return record_path.parent.name
    return None
