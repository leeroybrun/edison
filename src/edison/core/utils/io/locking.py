"""File locking utilities for atomic I/O operations."""
from __future__ import annotations

import fcntl
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, Optional

from .core import ensure_directory

_THREAD_MUTEXES: dict[str, threading.Lock] = {}
_FILE_LOCK_CONFIG_CACHE: Dict[str, Dict[str, Any]] = {}
_FILE_LOCK_CONFIG_MUTEX = threading.Lock()


class LockTimeoutError(TimeoutError):
    """Raised when an OS file lock cannot be acquired within timeout."""


def _thread_mutex(path: Path) -> threading.Lock:
    key = str(path.resolve())
    lock = _THREAD_MUTEXES.get(key)
    if lock is None:
        lock = _THREAD_MUTEXES.setdefault(key, threading.Lock())
    return lock


@contextmanager
def acquire_file_lock(
    file_path: Path | str,
    timeout: Optional[float] = None,
    nfs_safe: bool = True,
    *,
    fail_open: Optional[bool] = None,
    poll_interval: Optional[float] = None,
) -> Iterator[Optional[object]]:
    """Acquire an exclusive lock on ``file_path`` with a timeout.

    - Uses ``fcntl.flock`` with ``LOCK_EX | LOCK_NB`` (non-blocking) in a retry loop.
    - When ``nfs_safe`` is True, a sidecar ``.lock`` file is used for the lock target
      to avoid issues with NFS file locking semantics.
    - When ``fail_open`` is True, the context yields without raising after ``timeout``
      even if the lock could not be obtained (useful for deadlock resilience in tests).

    Args:
        file_path: Target file path to lock (or its .lock sidecar when nfs_safe=True).
        timeout: Maximum seconds to wait before raising ``LockTimeoutError``. Defaults to
            ``file_locking.timeout_seconds`` from configuration when omitted.
        nfs_safe: Use ``<file>.lock`` as the locked file.
        fail_open: If True, return control after ``timeout`` without raising. Defaults to
            ``file_locking.fail_open`` when omitted.
        poll_interval: Sleep duration between non-blocking attempts. Defaults to
            ``file_locking.poll_interval_seconds`` when omitted.

    Yields:
        The opened file object kept locked for the duration of the context.
    """
    cfg = get_file_locking_config()
    effective_timeout = timeout if timeout is not None else cfg["timeout_seconds"]
    effective_poll_interval = (
        poll_interval if poll_interval is not None else cfg["poll_interval_seconds"]
    )
    effective_fail_open = cfg["fail_open"] if fail_open is None else fail_open

    _validate_positive("timeout", effective_timeout)
    _validate_positive("poll_interval", effective_poll_interval)

    start = time.time()
    target = Path(file_path)
    lock_target = target.with_suffix(target.suffix + ".lock") if nfs_safe else target
    ensure_directory(lock_target.parent)

    mutex = _thread_mutex(lock_target)

    acquired_thread_lock = mutex.acquire(timeout=effective_timeout)
    if not acquired_thread_lock:
        if effective_fail_open:
            yield None
            return
        raise LockTimeoutError(
            f"Could not acquire lock on {target} within {effective_timeout}s"
        )

    fh = open(lock_target, "a+")
    acquired = False
    try:
        while True:
            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
                break
            except OSError:
                if (time.time() - start) >= effective_timeout:
                    if effective_fail_open:
                        break
                    raise LockTimeoutError(
                        f"Could not acquire lock on {target} within {effective_timeout}s"
                    )
                time.sleep(effective_poll_interval)

        yield fh if acquired else None
    finally:
        try:
            if acquired:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        finally:
            try:
                fh.close()
            finally:
                if nfs_safe:
                    try:
                        lock_target.unlink(missing_ok=True)
                    except Exception:
                        pass
            mutex.release()


def _validate_positive(name: str, value: float) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be positive (got {value})")


def get_file_locking_config() -> Dict[str, Any]:
    """Return the resolved file locking configuration for the current project root."""
    # Lazy import to avoid circular dependency
    from edison.core.config import ConfigManager

    mgr = ConfigManager()
    repo_key = str(mgr.repo_root)

    with _FILE_LOCK_CONFIG_MUTEX:
        cached = _FILE_LOCK_CONFIG_CACHE.get(repo_key)
        if cached is not None:
            return dict(cached)

        cfg = mgr.load_config(validate=False)
        section = cfg.get("file_locking")
        if not isinstance(section, dict):
            raise RuntimeError("file_locking section missing from configuration")

        try:
            timeout_seconds = float(section["timeout_seconds"])
            poll_interval_seconds = float(section["poll_interval_seconds"])
        except KeyError as exc:
            raise RuntimeError(
                "file_locking configuration must define timeout_seconds and poll_interval_seconds"
            ) from exc
        fail_open = bool(section.get("fail_open", False))

        _validate_positive("timeout_seconds", timeout_seconds)
        _validate_positive("poll_interval_seconds", poll_interval_seconds)

        result: Dict[str, Any] = {
            "timeout_seconds": timeout_seconds,
            "poll_interval_seconds": poll_interval_seconds,
            "fail_open": fail_open,
        }
        _FILE_LOCK_CONFIG_CACHE[repo_key] = result
        return dict(result)


__all__ = ["acquire_file_lock", "LockTimeoutError", "get_file_locking_config"]
