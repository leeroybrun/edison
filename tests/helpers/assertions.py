"""Custom assertion helpers for E2E tests."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional


def resolve_expected_path(path: Path) -> Path:
    """Resolve a possibly-global path to the actual location (session-aware).

    If the exact path exists, return it. Otherwise, search under
    .project/sessions/wip/*/{tasks,qa}/**/<basename> and return the first match.
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
        sessions_root = root / "sessions" / "wip"
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


def read_file(path: Path) -> str:
    """Read text from a path, resolving session-scoped location if needed."""
    actual = resolve_expected_path(path)
    return actual.read_text()


def assert_file_exists(path: Path, message: Optional[str] = None) -> None:
    """Assert file exists.

    Args:
        path: Path to file
        message: Custom error message

    Raises:
        AssertionError: If file doesn't exist
    """
    if path.exists():
        return
    # Session-aware fallback: if a global path isn't present, look under sessions/wip/*
    try:
        if ".project/tasks/" in str(path) or ".project/qa/" in str(path):
            root = next(p for p in path.parents if p.name == ".project")
            sessions_root = root / "sessions" / "wip"
            if sessions_root.exists():
                pattern = path.name
                # Search both tasks and qa subtree for the filename
                for domain in ("tasks", "qa"):
                    for candidate in sessions_root.glob(f"*/{domain}/**/{pattern}"):
                        if candidate.is_file():
                            return
    except Exception:
        pass
    if message is None:
        message = f"File does not exist: {path}"
    assert False, message


def assert_file_not_exists(path: Path, message: Optional[str] = None) -> None:
    """Assert file does not exist.

    Args:
        path: Path to file
        message: Custom error message

    Raises:
        AssertionError: If file exists
    """
    if message is None:
        message = f"File should not exist: {path}"
    assert not path.exists(), message


def assert_file_contains(path: Path, expected: str, message: Optional[str] = None) -> None:
    """Assert file contains expected string.

    Args:
        path: Path to file
        expected: Expected substring
        message: Custom error message

    Raises:
        AssertionError: If file doesn't contain expected string
    """
    assert_file_exists(path)
    content = read_file(path)
    if message is None:
        message = f"File {path} does not contain '{expected}'\nContent:\n{content}"
    assert expected in content, message


def assert_file_not_contains(path: Path, unexpected: str, message: Optional[str] = None) -> None:
    """Assert file does not contain string.

    Args:
        path: Path to file
        unexpected: String that should not be present
        message: Custom error message

    Raises:
        AssertionError: If file contains unexpected string
    """
    assert_file_exists(path)
    content = read_file(path)
    if message is None:
        message = f"File {path} should not contain '{unexpected}'\nContent:\n{content}"
    assert unexpected not in content, message


def assert_json_field(
    data: Dict[str, Any],
    field: str,
    expected: Any,
    message: Optional[str] = None
) -> None:
    """Assert JSON field has expected value.

    Args:
        data: JSON data dict
        field: Field name (supports dot notation for nested fields)
        expected: Expected value
        message: Custom error message

    Raises:
        AssertionError: If field doesn't match expected value
    """
    # Support dot notation for nested fields
    current = data
    parts = field.split(".")
    for part in parts[:-1]:
        assert part in current, f"Field path {field} not found in JSON"
        current = current[part]

    field_name = parts[-1]
    assert field_name in current, f"Field {field} not found in JSON"

    actual = current[field_name]
    if message is None:
        message = f"Field {field}: expected {expected}, got {actual}"
    assert actual == expected, message


def assert_json_has_field(
    data: Dict[str, Any],
    field: str,
    message: Optional[str] = None
) -> None:
    """Assert JSON has field (any value).

    Args:
        data: JSON data dict
        field: Field name (supports dot notation)
        message: Custom error message

    Raises:
        AssertionError: If field doesn't exist
    """
    # Support dot notation for nested fields
    current = data
    parts = field.split(".")
    for i, part in enumerate(parts):
        if message is None:
            path = ".".join(parts[:i+1])
            message = f"Field {path} not found in JSON data: {data}"
        assert part in current, message
        current = current[part]


def assert_json_array_contains(
    data: Dict[str, Any],
    field: str,
    expected_item: Any,
    message: Optional[str] = None
) -> None:
    """Assert JSON array field contains expected item.

    Args:
        data: JSON data dict
        field: Array field name
        expected_item: Item that should be in array
        message: Custom error message

    Raises:
        AssertionError: If array doesn't contain item
    """
    assert_json_has_field(data, field)

    # Get array value
    current = data
    for part in field.split("."):
        current = current[part]

    assert isinstance(current, list), f"Field {field} is not an array"

    if message is None:
        message = f"Array {field} does not contain {expected_item}\nArray: {current}"
    assert expected_item in current, message


def assert_list_length(
    items: List[Any],
    expected_length: int,
    message: Optional[str] = None
) -> None:
    """Assert list has expected length.

    Args:
        items: List to check
        expected_length: Expected length
        message: Custom error message

    Raises:
        AssertionError: If list length doesn't match
    """
    if message is None:
        message = f"Expected list length {expected_length}, got {len(items)}"
    assert len(items) == expected_length, message


def assert_list_contains(
    items: List[Any],
    expected_item: Any,
    message: Optional[str] = None
) -> None:
    """Assert list contains item.

    Args:
        items: List to check
        expected_item: Item that should be in list
        message: Custom error message

    Raises:
        AssertionError: If item not in list
    """
    if message is None:
        message = f"Expected item {expected_item} not in list: {items}"
    assert expected_item in items, message


def assert_list_not_contains(
    items: List[Any],
    unexpected_item: Any,
    message: Optional[str] = None
) -> None:
    """Assert list does not contain item.

    Args:
        items: List to check
        unexpected_item: Item that should not be in list
        message: Custom error message

    Raises:
        AssertionError: If item in list
    """
    if message is None:
        message = f"Unexpected item {unexpected_item} found in list: {items}"
    assert unexpected_item not in items, message


def assert_directory_exists(path: Path, message: Optional[str] = None) -> None:
    """Assert directory exists.

    Args:
        path: Path to directory
        message: Custom error message

    Raises:
        AssertionError: If directory doesn't exist
    """
    if message is None:
        message = f"Directory does not exist: {path}"
    assert path.exists() and path.is_dir(), message


def assert_directory_empty(path: Path, message: Optional[str] = None) -> None:
    """Assert directory is empty.

    Args:
        path: Path to directory
        message: Custom error message

    Raises:
        AssertionError: If directory not empty
    """
    assert_directory_exists(path)
    contents = list(path.iterdir())
    if message is None:
        message = f"Directory should be empty but contains: {contents}"
    assert len(contents) == 0, message


def assert_directory_not_empty(path: Path, message: Optional[str] = None) -> None:
    """Assert directory is not empty.

    Args:
        path: Path to directory
        message: Custom error message

    Raises:
        AssertionError: If directory is empty
    """
    assert_directory_exists(path)
    contents = list(path.iterdir())
    if message is None:
        message = f"Directory should not be empty: {path}"
    assert len(contents) > 0, message


def assert_symlink_exists(path: Path, message: Optional[str] = None) -> None:
    """Assert symlink exists.

    Args:
        path: Path to symlink
        message: Custom error message

    Raises:
        AssertionError: If symlink doesn't exist
    """
    if message is None:
        message = f"Symlink does not exist: {path}"
    assert path.is_symlink(), message


def assert_symlink_target(
    path: Path,
    expected_target: Path,
    message: Optional[str] = None
) -> None:
    """Assert symlink points to expected target.

    Args:
        path: Path to symlink
        expected_target: Expected target path
        message: Custom error message

    Raises:
        AssertionError: If symlink doesn't point to expected target
    """
    assert_symlink_exists(path)
    actual_target = path.readlink()
    if message is None:
        message = f"Symlink {path} points to {actual_target}, expected {expected_target}"
    assert actual_target == expected_target, message
