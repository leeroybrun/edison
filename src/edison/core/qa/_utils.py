"""Shared utilities for QA module.

This module contains helper functions used across the QA module to avoid duplication.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, List, Optional


def get_qa_root_path(project_root: Optional[Path] = None) -> Path:
    """Get QA root directory - single source of truth.

    This is the canonical way to resolve the QA root directory across
    all QA module components.

    Args:
        project_root: Optional project root path. If None, resolves automatically.

    Returns:
        Path to QA root directory (<project-management-dir>/qa or equivalent)
    """
    from edison.core.utils.paths import PathResolver, get_management_paths

    root = project_root or PathResolver.resolve_project_root()
    paths = get_management_paths(root)
    return paths.get_qa_root()


def get_evidence_base_path(project_root: Optional[Path] = None) -> Path:
    """Get base evidence directory path - single source of truth.

    Returns the base path where validation evidence is stored.
    The evidence subdirectory name comes from config (tasks.paths.evidenceSubdir).

    Path resolution:
    1. Uses ProjectManagementPaths.get_qa_root() as the QA base
    2. Appends the configured evidence subdirectory name

    This ensures consistency with other management-root relative paths
    while still allowing the evidence subdirectory name to be configured.

    Args:
        project_root: Optional project root path. If None, resolves automatically.

    Returns:
        Path to evidence base directory (e.g., <project-management-dir>/qa/<evidence-subdir>)

    Example:
        >>> base = get_evidence_base_path()
        >>> task_evidence = base / task_id
    """
    from edison.core.config.domains.task import TaskConfig
    from edison.core.utils.paths import PathResolver, get_management_paths

    root = project_root or PathResolver.resolve_project_root()
    cfg = TaskConfig(repo_root=root)
    evidence_subdir = cfg.evidence_subdir()

    # Use ProjectManagementPaths for consistent management-root relative paths
    # This ensures that when management_dir is customized, evidence paths follow
    mgmt_paths = get_management_paths(root)
    return mgmt_paths.get_qa_root() / evidence_subdir


def sort_round_dirs(dirs: Iterable[Path]) -> List[Path]:
    """Sort round directories by numeric suffix.

    Handles round-N directory names and sorts them numerically.
    Invalid names are sorted to the beginning with value -1.

    Args:
        dirs: Iterable of Path objects representing round directories

    Returns:
        Sorted list of Path objects

    Examples:
        >>> dirs = [Path("round-3"), Path("round-1"), Path("round-2")]
        >>> sort_round_dirs(dirs)
        [Path("round-1"), Path("round-2"), Path("round-3")]
    """
    def round_key(p: Path) -> int:
        try:
            parts = p.name.split("-")
            if len(parts) >= 2 and parts[-1].isdigit():
                return int(parts[-1])
            return -1
        except (ValueError, IndexError, AttributeError):
            return -1
    return sorted(dirs, key=round_key)


def read_json_safe(path: Path, default: Any = None) -> Any:
    """Safely read JSON with sensible defaults.

    Handles FileNotFoundError and JSONDecodeError gracefully by returning
    a default value instead of raising exceptions.

    Args:
        path: Path to JSON file
        default: Default value to return on error. If None, returns {}

    Returns:
        Parsed JSON data or default value

    Examples:
        >>> read_json_safe(Path("missing.json"))
        {}
        >>> read_json_safe(Path("missing.json"), default=[])
        []
    """
    from edison.core.utils.io import read_json

    try:
        return read_json(path)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default if default is not None else {}


def parse_primary_files(content: str) -> List[str]:
    """Extract primary files from task markdown content.

    This function parses task markdown to find the "Primary Files / Areas" section
    and extracts file paths from it. It handles multiple formats:

    1. Inline format: "Primary Files / Areas: file1, file2"
    2. Bulleted list format:
       ## Primary Files / Areas
       - file1
       - file2
    3. Alternative header: "- **Primary Files / Areas**"
    4. Combined inline + bulleted format

    Args:
        content: The task markdown content as a string.

    Returns:
        List of file paths extracted from the primary files section.
        Empty list if section not found or has no files.

    Examples:
        >>> content = '''
        ... ## Primary Files / Areas
        ... - src/app.ts
        ... - src/utils.ts
        ... '''
        >>> parse_primary_files(content)
        ['src/app.ts', 'src/utils.ts']

        >>> content = "Primary Files / Areas: src/main.ts, src/helper.ts"
        >>> parse_primary_files(content)
        ['src/main.ts', 'src/helper.ts']
    """
    files: List[str] = []
    capture = False

    for line in content.splitlines():
        # Check if this is the Primary Files / Areas header
        if "Primary Files / Areas" in line or "- **Primary Files" in line:
            capture = True

            # Handle inline format: "Primary Files / Areas: file1, file2"
            if ":" in line:
                parts = line.split(":", 1)
                if len(parts) > 1 and parts[1].strip():
                    # Extract comma-separated files from the inline format
                    inline_files = [f.strip() for f in parts[1].split(",") if f.strip()]
                    files.extend(inline_files)
            continue

        # Stop capturing at the next section header
        if capture and line.startswith("## "):
            break

        # Extract files from bullet points
        if capture and line.strip().startswith("-"):
            # Split on the first '-' and take the rest
            file_path = line.split("-", 1)[1].strip()
            if file_path:
                files.append(file_path)

    return files


__all__ = [
    "get_qa_root_path",
    "get_evidence_base_path",
    "sort_round_dirs",
    "read_json_safe",
    "parse_primary_files",
]
