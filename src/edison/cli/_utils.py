"""Shared CLI utility functions.

This module provides common utilities used across CLI commands to reduce
duplication and ensure consistent behavior.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional, Tuple, Union

from edison.core.utils.paths import resolve_project_root


def get_repo_root(args: argparse.Namespace) -> Path:
    """Get repository root from args or auto-detect.

    Args:
        args: Parsed arguments with optional repo_root attribute

    Returns:
        Path: Repository root path
    """
    if hasattr(args, "repo_root") and args.repo_root:
        return Path(args.repo_root).resolve()
    return resolve_project_root()


def validate_and_get_session_id(args: argparse.Namespace) -> str:
    """Validate and return session ID from args.

    Args:
        args: Parsed arguments with session_id attribute

    Returns:
        str: Validated session ID

    Raises:
        ValueError: If session ID is invalid
    """
    from edison.core.session.id import validate_session_id

    return validate_session_id(args.session_id)


def detect_record_type(record_id: str) -> str:
    """Auto-detect record type from ID format.

    Args:
        record_id: Record identifier

    Returns:
        str: 'qa' if ID contains '-qa' or ends with '.qa', else 'task'
    """
    if "-qa" in record_id or record_id.endswith(".qa"):
        return "qa"
    return "task"


def get_record_type(args: argparse.Namespace, record_id: str) -> str:
    """Get record type from args or auto-detect.

    Args:
        args: Parsed arguments with optional record_type attribute
        record_id: Record identifier for auto-detection

    Returns:
        str: Record type ('task' or 'qa')
    """
    if hasattr(args, "record_type") and args.record_type:
        return args.record_type
    return detect_record_type(record_id)


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
        from edison.core.qa.repository import QARepository

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


def run_cli_command(
    main_func,
    args: argparse.Namespace,
    *,
    error_code: str = "error",
) -> int:
    """Run CLI command with standard error handling.

    Args:
        main_func: Main function to execute (should return result dict or None)
        args: Parsed arguments
        error_code: Error code for JSON error output

    Returns:
        int: Exit code (0 for success, 1 for error)
    """
    from ._output import OutputFormatter

    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        result = main_func(args)
        if result is not None:
            formatter.json_output(result)
        return 0
    except Exception as e:
        formatter.error(e, error_code=error_code)
        return 1


__all__ = [
    "get_repo_root",
    "validate_and_get_session_id",
    "detect_record_type",
    "get_record_type",
    "get_repository",
    "normalize_record_id",
    "run_cli_command",
]
