"""Shared CLI utility functions.

This module provides common utilities used across CLI commands to reduce
duplication and ensure consistent behavior.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional, Union

from edison.core.utils.paths import resolve_project_root


def get_repo_root(args: argparse.Namespace) -> Path:
    """Get repository root from args or auto-detect.

    Args:
        args: Parsed arguments with optional repo_root/project_root attribute

    Returns:
        Path: Repository root path
    """
    # Canonical flag is --repo-root (attr: repo_root)
    if hasattr(args, "repo_root") and getattr(args, "repo_root"):
        return Path(getattr(args, "repo_root")).resolve()

    # Backward-compat for older call sites/tests that used "project_root"
    if hasattr(args, "project_root") and getattr(args, "project_root"):
        return Path(getattr(args, "project_root")).resolve()
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
    project_root: Optional[Path] = None,
) -> Union["TaskRepository", "QARepository"]:
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


__all__ = [
    "get_repo_root",
    "detect_record_type",
    "get_repository",
    "normalize_record_id",
]
