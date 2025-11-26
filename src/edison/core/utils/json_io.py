from __future__ import annotations

"""JSON I/O utilities with atomic writes and advisory locks."""

import fcntl
import json
from contextlib import nullcontext
from pathlib import Path
from typing import Any, Callable, Dict, ContextManager

from edison.core.file_io import utils as io_utils
from edison.core.file_io import locking as locklib
from edison.core.config.domains.timeouts import get_timeout_settings

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
    timeouts = get_timeout_settings()
    try:
        return float(timeouts["json_io_lock_seconds"])
    except KeyError as exc:
        raise RuntimeError("json_io_lock_seconds missing from timeout configuration") from exc


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


def read_json(file_path: Path | str) -> Any:
    """Read JSON with shared lock; raises FileNotFoundError on missing files."""
    path = Path(file_path)
    cfg = _cfg()
    if not path.exists():
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
    """Atomically write JSON to ``file_path`` honoring config formatting."""
    path = Path(file_path)
    cfg = _cfg().copy()
    
    if indent is not None:
        cfg["indent"] = indent
    if sort_keys is not None:
        cfg["sort_keys"] = sort_keys
    if ensure_ascii is not None:
        cfg["ensure_ascii"] = ensure_ascii

    io_utils._atomic_write(  # type: ignore[attr-defined]
        path,
        _json_writer(data, cfg),
        lock_cm=_lock_context(path, acquire_lock),
        encoding=cfg["encoding"],
    )


def update_json(file_path: Path | str, update_fn: Callable[[Dict[str, Any]], Dict[str, Any] | None]) -> None:
    """Read-modify-write helper with exclusive lock and atomic replacement."""
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

        io_utils._atomic_write(  # type: ignore[attr-defined]
            path,
            _json_writer(updated, cfg),
            lock_cm=nullcontext(),
            encoding=cfg["encoding"],
        )
