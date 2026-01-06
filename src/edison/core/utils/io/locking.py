"""File locking utilities for atomic I/O operations."""
from __future__ import annotations

import errno
import fcntl
import os
import shutil
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, Optional

from .core import ensure_directory
from typing import TextIO

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
    repo_root: Optional[Path] = None,
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
    cfg = get_file_locking_config(repo_root=repo_root)
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
                elapsed = time.time() - start
                remaining = effective_timeout - elapsed
                if remaining <= 0:
                    if effective_fail_open:
                        break
                    raise LockTimeoutError(
                        f"Could not acquire lock on {target} within {effective_timeout}s"
                    )
                # Avoid sleeping past the timeout budget. This matters for callers
                # that intentionally use very short timeouts (e.g. fail-open JSON I/O).
                time.sleep(min(effective_poll_interval, remaining))

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


def get_file_locking_config(repo_root: Optional[Path] = None) -> Dict[str, Any]:
    """Return the resolved file locking configuration.

    When ``repo_root`` is omitted, this resolves the active project root and
    loads config from there. This keeps behavior consistent in long-running
    processes and test suites that use isolated temp projects.
    """
    # Lazy import to avoid circular dependency
    from edison.core.config import ConfigManager
    from edison.core.utils.paths import resolve_project_root

    resolved_root = resolve_project_root() if repo_root is None else Path(repo_root).resolve()
    mgr = ConfigManager(repo_root=resolved_root)
    repo_key = str(resolved_root)

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


__all__ = ["acquire_file_lock", "LockTimeoutError", "get_file_locking_config", "file_lock", "is_locked", "safe_move_file", "write_text_locked"]


def is_locked(target: Path) -> bool:
    """Return True when a lock file exists for target."""
    target = Path(target)
    lock_path = target.with_suffix(target.suffix + ".lock")
    return lock_path.exists()


@contextmanager
def file_lock(target: Path, timeout: float = 10.0) -> Iterator[Path]:
    """Create an exclusive lock for the target using sidecar .lock file.
    
    This is a simplified wrapper around acquire_file_lock that yields the
    target path on success and raises SystemExit when the lock cannot be
    acquired within timeout.
    
    Args:
        target: File path to lock
        timeout: Maximum seconds to wait for lock
        
    Yields:
        The target path (for convenience)
        
    Raises:
        SystemExit: If lock cannot be acquired within timeout
    """
    lock_cm = acquire_file_lock(Path(target), timeout=timeout)
    try:
        lock_cm.__enter__()
    except LockTimeoutError as e:
        raise SystemExit(f"File is locked: {target}") from e
    try:
        yield target
    finally:
        lock_cm.__exit__(None, None, None)


def safe_move_file(src: Path, dest: Path, repo_root: Optional[Path] = None) -> Path:
    """Atomically move a file, preferring git mv when available.
    
    Args:
        src: Source file path
        dest: Destination file path
        repo_root: Repository root for git operations (auto-detected if None)
        
    Returns:
        The destination path
    """
    src = Path(src)
    dest = Path(dest)
    ensure_directory(dest.parent)
    
    # Try git mv first
    if repo_root is None:
        try:
            from edison.core.utils.paths import PathResolver
            repo_root = PathResolver.resolve_project_root()
        except Exception:
            repo_root = None
    
    if repo_root is not None:
        try:
            from edison.core.utils.subprocess import run_with_timeout
            result = run_with_timeout(
                ["git", "mv", "--", str(src), str(dest)],
                cwd=repo_root,
                check=True,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return dest
        except Exception:
            pass
    
    # Fallback to os.replace
    try:
        os.replace(str(src), str(dest))
        return dest
    except OSError as e:
        if e.errno == errno.EXDEV:
            # Cross-device move: copy + verify + delete
            shutil.copy2(str(src), str(dest))
            # Verify by comparing content to detect corruption
            src_content = src.read_bytes()
            dest_content = dest.read_bytes()
            if src_content != dest_content:
                dest.unlink(missing_ok=True)
                raise RuntimeError("Cross-device move verification failed - content mismatch") from e
            src.unlink(missing_ok=True)
            return dest
        raise


def write_text_locked(path: Path, content: str) -> None:
    """Write text atomically while holding an exclusive lock on the target.

    Uses the existing atomic_write implementation from core module with
    file_lock as the locking context manager to avoid code duplication.

    Args:
        path: Target file path
        content: Text content to write
    """
    from .core import atomic_write

    target = Path(path)

    def _writer(f: TextIO) -> None:
        f.write(content)

    atomic_write(target, _writer, lock_cm=file_lock(target))
