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
from pathlib import PurePosixPath
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
    file_posix = str(PurePosixPath(file_path))
    pattern_posix = str(PurePosixPath(pattern))

    # Expand simple brace patterns like "*.{ts,tsx}".
    expanded = _expand_braces(pattern_posix)

    for pat in expanded:
        # Strip leading slash (treat as repo-root relative)
        if pat.startswith("/"):
            pat = pat[1:]

        # 1) Glob-style match with '**' support.
        # pathlib's '**' semantics differ slightly from typical bash globstar for patterns like
        # "apps/api/**/*" (it may not match direct children). We generate a small set of
        # compatible variants (e.g., also try "apps/api/*").
        for glob_pat in _expand_globstar_variants(pat):
            try:
                if PurePosixPath(file_posix).match(glob_pat):
                    return True
            except Exception:
                pass

        # 2) If pattern is a bare filename glob, also try matching anywhere in the path.
        if "/" not in pat and not pat.startswith("**"):
            try:
                if PurePosixPath(file_posix).match(f"**/{pat}"):
                    return True
            except Exception:
                pass

        # 3) Final fallback: fnmatch (keeps legacy semantics in edge cases).
        if fnmatch.fnmatch(file_posix, pat):
            return True
        if fnmatch.fnmatch(Path(file_posix).name, pat):
            return True

    return False


def _expand_braces(pattern: str) -> list[str]:
    """Expand a single-level brace group like 'foo.{a,b}' into ['foo.a', 'foo.b'].

    Supports multiple brace groups via recursion.
    If no braces are present, returns [pattern].
    """
    start = pattern.find("{")
    if start == -1:
        return [pattern]
    end = pattern.find("}", start + 1)
    if end == -1:
        return [pattern]

    before = pattern[:start]
    inside = pattern[start + 1 : end]
    after = pattern[end + 1 :]

    # Empty or non-comma group → no expansion
    parts = [p.strip() for p in inside.split(",") if p.strip()]
    if len(parts) <= 1:
        return [pattern]

    out: list[str] = []
    for part in parts:
        out.extend(_expand_braces(f"{before}{part}{after}"))
    return out


def _expand_globstar_variants(pattern: str) -> list[str]:
    """Return globstar-compatible variants for patterns containing '/**/'.

    pathlib.Path.match can treat '**' as requiring at least one component when used as '/**/'.
    In Edison configs we commonly use patterns like 'apps/api/**/*' which are intended to match
    both direct and nested children. To preserve that intent, we also try a variant with '/**/'
    collapsed to '/' (e.g. 'apps/api/*').
    """
    if "/**/" not in pattern:
        return [pattern]
    # Collapse all occurrences; this is sufficient for our config style (one globstar segment).
    collapsed = pattern.replace("/**/", "/")
    if collapsed == pattern:
        return [pattern]
    return [pattern, collapsed]


__all__ = [
    "match_patterns",
    "matches_any_pattern",
    "find_matching_pattern",
    "filter_files_by_patterns",
]
