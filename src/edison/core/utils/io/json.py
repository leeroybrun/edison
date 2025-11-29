"""JSON I/O utilities with atomic writes and advisory locks."""
from __future__ import annotations

import fcntl
import json
from contextlib import nullcontext
from pathlib import Path
from typing import Any, Callable, ContextManager, Dict

from . import locking as locklib
from .core import atomic_write

# Default configuration (can be overridden by passing config to functions)
DEFAULT_JSON_CONFIG: Dict[str, Any] = {
    "indent": 2,
    "sort_keys": True,
    "ensure_ascii": False,
    "encoding": "utf-8",
}


def _cfg() -> Dict[str, Any]:
    """Return default JSON I/O configuration.

    Note: ConfigManager is intentionally not imported here to avoid circular
    dependencies. Callers can override defaults by setting module-level config.
    """
    return DEFAULT_JSON_CONFIG


def _lock_timeout_seconds() -> float:
    # Lazy import to avoid circular dependency with config
    from edison.core.config.domains.timeouts import TimeoutsConfig

    timeout_config = TimeoutsConfig()
    return timeout_config.json_io_lock_seconds


def _lock_context(path: Path, acquire_lock: bool) -> ContextManager[Any]:
    if not acquire_lock:
        return nullcontext()
    return locklib.acquire_file_lock(
        path, timeout=_lock_timeout_seconds(), fail_open=True
    )


def _json_writer(data: Any, cfg: Dict[str, Any]) -> Callable[[Any], None]:
    def _writer(f):
        json.dump(
            data,
            f,
            indent=cfg["indent"],
            sort_keys=cfg["sort_keys"],
            ensure_ascii=cfg["ensure_ascii"],
        )

    return _writer


_MISSING = object()  # Sentinel for unset default


def read_json(file_path: Path | str, *, default: Any = _MISSING) -> Any:
    """Read JSON with shared lock.

    Args:
        file_path: Path to JSON file
        default: Value to return if file doesn't exist (optional).
                 If not provided, FileNotFoundError is raised.

    Returns:
        Parsed JSON data, or ``default`` if file doesn't exist

    Raises:
        FileNotFoundError: If the file does not exist and no default is provided
    """
    path = Path(file_path)
    cfg = _cfg()
    if not path.exists():
        if default is not _MISSING:
            return default
        raise FileNotFoundError(f"JSON file not found: {path}")

    with open(path, "r", encoding=cfg["encoding"]) as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_SH)
        data = json.load(f)
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    return data


def write_json_atomic(
    file_path: Path | str,
    data: Any,
    *,
    acquire_lock: bool = True,
    indent: int | None = None,
    sort_keys: bool | None = None,
    ensure_ascii: bool | None = None,
) -> None:
    """Atomically write JSON to ``file_path`` honoring config formatting.

    Args:
        file_path: Target file path
        data: Data to serialize as JSON
        acquire_lock: Whether to acquire a file lock (default: True)
        indent: JSON indentation (default: 2)
        sort_keys: Sort object keys (default: True)
        ensure_ascii: Escape non-ASCII characters (default: False)
    """
    path = Path(file_path)
    cfg = _cfg().copy()

    if indent is not None:
        cfg["indent"] = indent
    if sort_keys is not None:
        cfg["sort_keys"] = sort_keys
    if ensure_ascii is not None:
        cfg["ensure_ascii"] = ensure_ascii

    atomic_write(
        path,
        _json_writer(data, cfg),
        lock_cm=_lock_context(path, acquire_lock),
        encoding=cfg["encoding"],
    )


def update_json(
    file_path: Path | str,
    update_fn: Callable[[Dict[str, Any]], Dict[str, Any] | None],
) -> None:
    """Read-modify-write helper with exclusive lock and atomic replacement.

    Args:
        file_path: Path to JSON file
        update_fn: Function that receives the current data and returns updated data.
                   If it returns None, the current data is kept unchanged.
    """
    path = Path(file_path)
    cfg = _cfg()

    with _lock_context(path, acquire_lock=True):
        current: Dict[str, Any] = {}
        if path.exists():
            current_obj = read_json(path)
            if isinstance(current_obj, dict):
                current = dict(current_obj)
            else:
                current = {"value": current_obj}

        updated = update_fn(current)
        if updated is None:
            updated = current

        atomic_write(
            path,
            _json_writer(updated, cfg),
            lock_cm=nullcontext(),
            encoding=cfg["encoding"],
        )


__all__ = [
    "DEFAULT_JSON_CONFIG",
    "read_json",
    "write_json_atomic",
    "update_json",
]



