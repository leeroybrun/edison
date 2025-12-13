"""Unified file pattern matching - single source of truth.

This module provides all fnmatch-based pattern matching operations
for the Edison framework. All file pattern matching should use these
functions instead of direct fnmatch calls.

Example:
    from edison.core.utils.patterns import match_patterns, matches_any_pattern

    # Match files against triggers
    matched = match_patterns(["src/app.tsx", "lib/utils.py"], ["*.tsx", "*.py"])

    # Check if a file matches any pattern
    if matches_any_pattern("src/components/Button.tsx", ["**/*.tsx"]):
        print("React component detected")
"""
from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Optional


def match_patterns(files: list[str], patterns: list[str]) -> list[str]:
    """Match files against glob patterns. Returns matching files.

    Args:
        files: List of file paths (relative to repo root)
        patterns: List of glob patterns (e.g., ["**/*.tsx", "**/components/**/*"])

    Returns:
        List of files that match at least one pattern
    """
    if not files or not patterns:
        return []

    # "*" means always run - all files match
    if "*" in patterns:
        return list(files)

    matched = []
    for file_path in files:
        for pattern in patterns:
            if _matches_pattern(file_path, pattern):
                matched.append(file_path)
                break
    return matched


def matches_any_pattern(file_path: str, patterns: list[str]) -> bool:
    """Check if file matches any pattern.

    Args:
        file_path: File path to check
        patterns: List of glob patterns

    Returns:
        True if file matches at least one pattern
    """
    if not patterns:
        return False

    # "*" means always run
    if "*" in patterns:
        return True

    for pattern in patterns:
        if _matches_pattern(file_path, pattern):
            return True
    return False


def find_matching_pattern(file_path: str, patterns: list[str]) -> Optional[str]:
    """Find first matching pattern for a file.

    Args:
        file_path: File path to check
        patterns: List of glob patterns

    Returns:
        First matching pattern, or None if no match
    """
    if not patterns:
        return None

    # "*" means always run
    if "*" in patterns:
        return "*"

    for pattern in patterns:
        if _matches_pattern(file_path, pattern):
            return pattern
    return None


def filter_files_by_patterns(
    files: list[str], patterns: list[str]
) -> dict[str, list[str]]:
    """Group files by which pattern they matched.

    Args:
        files: List of file paths
        patterns: List of glob patterns

    Returns:
        Dict mapping pattern -> list of matched files.
        Unmatched files are under the "_unmatched" key.
    """
    result: dict[str, list[str]] = {p: [] for p in patterns}
    result["_unmatched"] = []

    for file_path in files:
        matched = False
        for pattern in patterns:
            if _matches_pattern(file_path, pattern):
                result[pattern].append(file_path)
                matched = True
                break
        if not matched:
            result["_unmatched"].append(file_path)
    return result


def _matches_pattern(file_path: str, pattern: str) -> bool:
    """Internal helper to check if a file matches a pattern.

    Handles various pattern formats:
    - Direct fnmatch: "*.tsx" matches "Button.tsx"
    - Path prefix: "src/*.tsx" matches "src/Button.tsx"
    - Recursive: "**/*.tsx" matches "src/components/Button.tsx"
    - Filename only: "*.tsx" matches "src/Button.tsx" via filename

    Args:
        file_path: File path to check
        pattern: Glob pattern

    Returns:
        True if file matches pattern
    """
    # Direct match
    if fnmatch.fnmatch(file_path, pattern):
        return True

    # Try with leading ** if pattern doesn't have it
    # This handles patterns like "*.tsx" matching "src/components/Button.tsx"
    if not pattern.startswith("**") and not pattern.startswith("/"):
        if fnmatch.fnmatch(file_path, f"**/{pattern}"):
            return True
        # Try just matching the filename
        if fnmatch.fnmatch(Path(file_path).name, pattern):
            return True

    return False


__all__ = [
    "match_patterns",
    "matches_any_pattern",
    "find_matching_pattern",
    "filter_files_by_patterns",
]
