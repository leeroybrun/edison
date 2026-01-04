"""Shared CLI utility functions.

This module provides common utilities used across CLI commands to reduce
duplication and ensure consistent behavior.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import TYPE_CHECKING

from edison.core.utils.paths import resolve_project_root

if TYPE_CHECKING:
    from edison.core.qa.workflow.repository import QARepository
    from edison.core.task.repository import TaskRepository


def get_repo_root(args: argparse.Namespace) -> Path:
    """Get repository root from args or auto-detect.

    Args:
        args: Parsed arguments with optional repo_root/project_root attribute

    Returns:
        Path: Repository root path
    """
    # Canonical flag is --repo-root (attr: repo_root)
    if hasattr(args, "repo_root") and args.repo_root:
        return Path(args.repo_root).resolve()

    # Backward-compat for older call sites/tests that used "project_root"
    if hasattr(args, "project_root") and args.project_root:
        return Path(args.project_root).resolve()
    return resolve_project_root()


def detect_record_type(record_id: str) -> str:
    """Auto-detect record type from ID format.

    Args:
        record_id: Record identifier

    Returns:
        str: 'qa' if ID is a QA record ID, else 'task'
    """
    # QA record IDs are derived from the task ID and use a reserved suffix:
    #   - "<task_id>-qa" (most common)
    #   - "<task_id>.qa" (alternate form)
    #
    # IMPORTANT: Task slugs may legitimately contain "qa" in the middle (e.g. "...-qa-promote"),
    # so we MUST NOT treat a mere substring match as a QA record.
    if record_id.endswith("-qa") or record_id.endswith(".qa"):
        return "qa"
    return "task"


def get_repository(
    record_type: str,
    project_root: Path | None = None,
) -> TaskRepository | QARepository:
    """Get appropriate repository instance for record type.

    Args:
        record_type: 'task' or 'qa'
        project_root: Optional project root override

    Returns:
        Repository instance

    Raises:
        ValueError: If record_type is invalid
    """
    if record_type == "qa":
        from edison.core.qa.workflow.repository import QARepository

        return QARepository(project_root=project_root)
    elif record_type == "task":
        from edison.core.task.repository import TaskRepository

        return TaskRepository(project_root=project_root)
    else:
        raise ValueError(f"Invalid record type: {record_type}")


def normalize_record_id(record_type: str, record_id: str) -> str:
    """Normalize record ID to canonical format.

    Args:
        record_type: 'task' or 'qa'
        record_id: Raw record identifier

    Returns:
        str: Normalized record ID
    """
    from edison.core.task import normalize_record_id as _normalize

    return _normalize(record_type, record_id)


def resolve_existing_task_id(*, project_root: Path, raw_task_id: str) -> str:
    """Resolve a task id that must already exist.

    Supports fail-closed shorthand resolution:
    - exact id match
    - unique prefix match of the form "<token>-*" (e.g. "12007" -> "12007-wave8-...")
    """
    from edison.core.config.domains import TaskConfig
    from edison.core.session.paths import get_session_bases
    from edison.core.task.repository import TaskRepository

    token = normalize_record_id("task", raw_task_id)
    repo = TaskRepository(project_root=project_root)

    if repo.exists(token):
        return token

    cfg = TaskConfig(repo_root=project_root)
    states = cfg.task_states()
    tasks_root = cfg.tasks_root()

    def _scan_dir(dir_path: Path, prefix: str) -> set[str]:
        if not dir_path.exists():
            return set()
        return {p.stem for p in dir_path.glob(f"{prefix}*{repo.file_extension}") if p.is_file()}

    # Shorthand resolution is intentionally conservative: by default we only match
    # "<token>-*" since Edison canonical ids are "<numeric-prefix>-<slug>".
    prefix = f"{token}-"
    matches_set: set[str] = set()

    # Global tasks
    for st in states:
        matches_set |= _scan_dir(tasks_root / st, prefix)

    # Session-scoped tasks
    for base in get_session_bases(project_root=project_root):
        for st in states:
            matches_set |= _scan_dir(base / "tasks" / st, prefix)

    matches = sorted(matches_set)
    if len(matches) == 1:
        return matches[0]

    if matches:
        shown = matches[:10]
        more = "" if len(matches) <= 10 else f"\n  ... and {len(matches) - 10} more"
        raise ValueError(
            f"Ambiguous task id '{raw_task_id}' (matches {len(matches)} tasks). "
            "Use a longer prefix or the full id.\n"
            + "\n".join(f"  - {m}" for m in shown)
            + more
        )

    raise ValueError(
        f"Task not found: {token}\n"
        "Tip: run `edison task similar <token>` to search for matching tasks."
    )


def format_display_path(*, project_root: Path, path: Path) -> str:
    """Format a user-friendly path for CLI output.

    Prefers showing the path via the configured management directory (usually
    `.project`) so users/LLMs can locate files in the current worktree even when
    the management dir is backed by a shared meta worktree.
    """
    p = Path(path)
    try:
        if p.is_relative_to(project_root):
            return str(p.relative_to(project_root))
    except Exception:
        pass

    # Map meta worktree paths back to the management directory symlink when possible.
    try:
        from edison.core.utils.paths import get_management_paths

        mgmt = get_management_paths(project_root)
        logical_root = mgmt.get_management_root_unresolved()
        resolved_root = mgmt.get_management_root()

        resolved_path = p.resolve()
        rel = resolved_path.relative_to(resolved_root)
        logical_path = logical_root / rel
        if logical_path.exists():
            try:
                if logical_path.is_relative_to(project_root):
                    return str(logical_path.relative_to(project_root))
            except Exception:
                pass
            return str(logical_path)
    except Exception:
        pass

    return str(p)


def resolve_session_id(
    *,
    project_root: Path,
    explicit: str | None = None,
    required: bool = False,
) -> str | None:
    """Resolve a session id using the canonical core resolution order.

    Resolution (core): explicit → AGENTS_SESSION → `<project-management-dir>/.session-id` → process-derived lookup.

    Semantics:
    - If `explicit` is provided, it is treated as authoritative and MUST exist (fail-closed).
    - If `required=True`, a session MUST be resolvable and MUST exist.
    - Otherwise, returns an existing inferred session id when available, or None.
    """
    from edison.core.session.core.id import require_session_id

    if explicit:
        return require_session_id(explicit=explicit, project_root=project_root)

    if required:
        return require_session_id(project_root=project_root)

    from edison.core.session.core.id import detect_session_id

    return detect_session_id(project_root=project_root)


__all__ = [
    "get_repo_root",
    "detect_record_type",
    "get_repository",
    "normalize_record_id",
    "resolve_existing_task_id",
    "format_display_path",
    "resolve_session_id",
]
