"""
Higher-level IO utilities for Edison core.

This module will wrap lower-level helpers from :mod:`lib.io_utils` to
provide cohesive operations for the new domain packages.
"""
from __future__ import annotations

from pathlib import Path
from typing import Union

from .. import io_utils as _io_utils


PathLike = Union[str, Path]


def read_text(path: PathLike) -> str:
    """Read a UTF‑8 text file with simple, explicit error handling.

    - Missing files raise :class:`FileNotFoundError`
    - Other I/O errors are propagated to callers
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Text file not found: {path}")
    return path.read_text(encoding="utf-8")


def write_text(path: PathLike, content: str) -> None:
    """Atomically write UTF‑8 text to ``path``.

    This delegates to the core :mod:`lib.io_utils` atomic writer so that
    text files benefit from the same crash‑safety guarantees as JSON/YAML:

    - Parent directory is created if missing
    - Data is written to a temp file alongside the target
    - Temp file is fsync'd and atomically renamed into place
    """
    target = Path(path)

    def _writer(f) -> None:
        f.write(content)

    # Reuse the shared atomic writer from io_utils for consistency.
    atomic_write = getattr(_io_utils, "_atomic_write", None)
    if atomic_write is not None:
        atomic_write(target, _writer)  # type: ignore[misc]
    else:
        # Fallback: best‑effort non‑atomic write while still ensuring the
        # parent directory exists. This branch is unlikely in practice.
        _io_utils.ensure_parent_dir(target)
        target.write_text(content, encoding="utf-8")


def ensure_directory(path: PathLike) -> Path:
    """Ensure a directory exists, creating it (and parents) if needed.

    Returns the directory path as a :class:`Path` instance.
    """
    return _io_utils.ensure_directory(Path(path))

