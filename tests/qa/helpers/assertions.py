from __future__ import annotations

from pathlib import Path
from typing import Optional, Any, Dict


def resolve_expected_path(path: Path) -> Path:
    if path.exists():
        return path
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
    return resolve_expected_path(path).read_text()


def assert_file_exists(path: Path, message: Optional[str] = None) -> None:
    if resolve_expected_path(path).exists():
        return
    if message is None:
        message = f"File does not exist: {path}"
    assert False, message


def assert_file_contains(path: Path, expected: str, message: Optional[str] = None) -> None:
    content = read_file(path)
    if message is None:
        message = f"File {path} does not contain '{expected}'\nContent:\n{content}"
    assert expected in content, message


def assert_file_not_contains(path: Path, unexpected: str, message: Optional[str] = None) -> None:
    content = read_file(path)
    if message is None:
        message = f"File {path} should not contain '{unexpected}'\nContent:\n{content}"
    assert unexpected not in content, message

