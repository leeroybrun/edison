"""File I/O utilities for Edison core.

Single source of truth for safe file access patterns:
- Atomic writes with fsync and advisory locks
- Safe reads with shared locks and fast failure on missing files
- YAML support with consistent error handling
- Directory management utilities
- Canonical UTC timestamp helper

See `.project/qa/EDISON_NO_LEGACY_POLICY.md` for configuration and migration rules.
"""
from __future__ import annotations

import fcntl
import os
import tempfile
from contextlib import nullcontext
from pathlib import Path
from typing import Any, Dict, Optional, Callable, TextIO, ContextManager, Union

try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False


PathLike = Union[str, Path]

_DEFAULT_SENTINEL: object = object()


def ensure_parent_dir(path: Path) -> None:
    """Ensure the parent directory for ``path`` exists.

    This is a small helper used by all atomic writers in this module to avoid
    re-implementing the ``mkdir(parents=True, exist_ok=True)`` pattern.
    """
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def _atomic_write(
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


def write_json_safe(
    path: Path, 
    data: Any, 
    indent: int = 2, 
    *, 
    acquire_lock: bool = True, 
    sort_keys: bool = True, 
    ensure_ascii: bool = False
) -> None:
    """Atomically write JSON data to ``path`` (delegates to lib.utils.json_io)."""
    from ..utils import json_io  # Lazy import to avoid cycles

    json_io.write_json_atomic(
        Path(path), 
        data, 
        acquire_lock=acquire_lock, 
        indent=indent, 
        sort_keys=sort_keys, 
        ensure_ascii=ensure_ascii
    )


def read_json_safe(path: Path, default: Any = _DEFAULT_SENTINEL) -> Any:
    """Safely read JSON with shared lock.

    When ``default`` is provided any error returns that default value,
    otherwise exceptions propagate. Delegates to ``lib.utils.json_io``.
    """
    from ..utils import json_io  # Lazy import to avoid cycles

    try:
        return json_io.read_json(Path(path))
    except Exception:
        if default is _DEFAULT_SENTINEL:
            raise
        return default


def utc_timestamp() -> str:
    """Return ISO 8601 UTC timestamp (delegates to lib.utils.time)."""
    from ..utils import time as time_utils  # type: ignore

    return time_utils.utc_timestamp()


# ============================================================================
# YAML I/O
# ============================================================================

def read_yaml_safe(path: Path, default: Any = None) -> Any:
    """Read YAML with error handling.

    Returns default if file is missing or invalid.

    Args:
        path: YAML file path to read
        default: Value to return if file missing or invalid (default: None)

    Returns:
        Any: Parsed YAML data, or default if error

    Examples:
        >>> config = read_yaml_safe(Path("config.yaml"), default={})
        >>> assert isinstance(config, dict)
    """
    if not HAS_YAML:
        return default

    path = Path(path)
    if not path.exists():
        return default

    try:
        with open(path, "r", encoding="utf-8") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            data = yaml.safe_load(f)  # type: ignore[no-untyped-call]
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        return data if data is not None else default
    except Exception:
        return default


def write_yaml_safe(path: Path, data: Any) -> None:
    """Atomically write YAML data to ``path``.

    Matches the JSON helper by using the shared atomic writer. Keys are
    sorted for deterministic output.
    """
    if not HAS_YAML:
        raise RuntimeError(
            "PyYAML is required for YAML operations. Install with: pip install pyyaml"
        )

    def _writer(f: TextIO) -> None:
        yaml.safe_dump(  # type: ignore[no-untyped-call]
            data,
            f,
            default_flow_style=False,
            sort_keys=True,
            allow_unicode=True,
        )

    _atomic_write(Path(path), _writer)


# ============================================================================
# Directory management
# ============================================================================

def ensure_directory(path: Path, create: bool = True) -> Path:
    """Ensure directory exists.

    Args:
        path: Directory path to check/create
        create: If True, create directory if missing; if False, raise if missing

    Returns:
        Path: The directory path (guaranteed to exist if create=True)

    Raises:
        FileNotFoundError: If create=False and directory doesn't exist
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


def ensure_dir(path: Path) -> Path:
    """Ensure directory exists, creating if necessary.

    Args:
        path: Directory path to ensure exists

    Returns:
        The path (for chaining)
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


# ============================================================================
# Enhanced JSON I/O with defaults
# ============================================================================

def read_json_with_default(path: Path, default: Optional[Any] = None) -> Any:
    """Read JSON with error handling and default fallback.

    Unlike read_json_safe, this returns a default value on any error
    (missing file, invalid JSON, etc.) instead of raising exceptions.

    Args:
        path: JSON file path to read
        default: Value to return if file missing or invalid (default: None)

    Returns:
        Any: Parsed JSON data, or default if error

    Examples:
        >>> config = read_json_with_default(Path("config.json"), default={})
        >>> assert isinstance(config, dict)
    """
    return read_json_safe(path, default=default)


# ============================================================================
# Higher-level text utilities
# ============================================================================

def read_text(path: PathLike) -> str:
    """Read a UTF-8 text file with simple, explicit error handling.

    - Missing files raise :class:`FileNotFoundError`
    - Other I/O errors are propagated to callers
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
    """
    target = Path(path)

    def _writer(f) -> None:
        f.write(content)

    _atomic_write(target, _writer)


__all__ = [
    "ensure_parent_dir",
    "_atomic_write",
    "write_json_safe",
    "read_json_safe",
    "utc_timestamp",
    "read_yaml_safe",
    "write_yaml_safe",
    "ensure_directory",
    "ensure_dir",
    "read_json_with_default",
    "read_text",
    "write_text",
    "PathLike",
    "HAS_YAML",
]
