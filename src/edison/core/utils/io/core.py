"""Core I/O utilities for Edison.

Single source of truth for safe file access patterns:
- Atomic writes with fsync and advisory locks
- Text file read/write operations
- Directory management utilities

This module provides the foundational I/O primitives used by json.py and yaml.py.
"""
from __future__ import annotations

import fcntl
import os
import tempfile
from contextlib import nullcontext
from pathlib import Path
from typing import Any, Callable, ContextManager, Optional, TextIO, Union

PathLike = Union[str, Path]


def ensure_parent_dir(path: Path) -> None:
    """Ensure the parent directory for ``path`` exists.

    This is a small helper used by all atomic writers in this module to avoid
    re-implementing the ``mkdir(parents=True, exist_ok=True)`` pattern.
    """
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def ensure_directory(path: Path, create: bool = True) -> Path:
    """Ensure directory exists.

    Args:
        path: Directory path to check/create
        create: If True, create directory if missing; if False, raise if missing

    Returns:
        Path: The directory path (guaranteed to exist if create=True)

    Raises:
        FileNotFoundError: If create=False and directory doesn't exist
        NotADirectoryError: If path exists but is not a directory
        OSError: If directory creation fails

    Examples:
        >>> data_dir = ensure_directory(Path(".project/data"))
        >>> assert data_dir.exists()

        >>> # Fail-fast mode
        >>> ensure_directory(Path("/nonexistent"), create=False)  # raises
    """
    path = Path(path)

    if path.exists():
        if not path.is_dir():
            raise NotADirectoryError(f"Path exists but is not a directory: {path}")
        return path

    if create:
        path.mkdir(parents=True, exist_ok=True)
        return path
    else:
        raise FileNotFoundError(f"Directory does not exist: {path}")


def atomic_write(
    path: Path,
    write_fn: Callable[[TextIO], None],
    *,
    lock_cm: Optional[ContextManager[Any]] = None,
    encoding: str = "utf-8",
) -> None:
    """Write to ``path`` atomically using a temp file + fsync + rename.

    This helper is the single implementation for crash-safe writes:
    - Parent directory is created if missing
    - Data is written to a temporary file in the same directory
    - File is fsync'd, unlocked, then atomically replaced
    - Any leftover temp file is cleaned up on failure
    - ``encoding`` controls the temp file text encoding (default: UTF-8)

    Args:
        path: Target file path
        write_fn: Callable that writes content to the file object
        lock_cm: Optional context manager for file locking
        encoding: Text encoding (default: utf-8)
    """
    path = Path(path)
    ensure_parent_dir(path)

    lock_context = lock_cm or nullcontext()
    tmp_path: Optional[Path] = None
    try:
        with lock_context:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding=encoding,
                dir=str(path.parent),
                delete=False,
            ) as f:
                tmp_path = Path(f.name)
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                write_fn(f)
                f.flush()
                os.fsync(f.fileno())
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

            os.replace(str(tmp_path), str(path))
    finally:
        if tmp_path is not None and tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                # Best-effort cleanup; never fail callers on temp removal
                pass


def read_text(path: PathLike) -> str:
    """Read a UTF-8 text file with simple, explicit error handling.

    Args:
        path: Path to the text file

    Returns:
        str: File contents

    Raises:
        FileNotFoundError: If the file does not exist
        Other I/O errors are propagated to callers
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Text file not found: {path}")
    return path.read_text(encoding="utf-8")


def write_text(path: PathLike, content: str) -> None:
    """Atomically write UTF-8 text to ``path``.

    This uses the atomic writer so that text files benefit from the same
    crash-safety guarantees as JSON/YAML:

    - Parent directory is created if missing
    - Data is written to a temp file alongside the target
    - Temp file is fsync'd and atomically renamed into place

    Args:
        path: Target file path
        content: Text content to write
    """
    target = Path(path)

    def _writer(f: TextIO) -> None:
        f.write(content)

    atomic_write(target, _writer)


__all__ = [
    "PathLike",
    "ensure_parent_dir",
    "ensure_directory",
    "atomic_write",
    "read_text",
    "write_text",
]
