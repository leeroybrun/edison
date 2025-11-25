from __future__ import annotations

import fcntl
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional


_THREAD_MUTEXES: dict[str, threading.Lock] = {}


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
    timeout: float = 10.0,
    nfs_safe: bool = True,
    *,
    fail_open: bool = False,
    poll_interval: float = 0.1,
) -> Iterator[Optional[object]]:
    """Acquire an exclusive lock on ``file_path`` with a timeout.

    - Uses ``fcntl.flock`` with ``LOCK_EX | LOCK_NB`` (non-blocking) in a retry loop.
    - When ``nfs_safe`` is True, a sidecar ``.lock`` file is used for the lock target
      to avoid issues with NFS file locking semantics.
    - When ``fail_open`` is True, the context yields without raising after ``timeout``
      even if the lock could not be obtained (useful for deadlock resilience in tests).

    Args:
        file_path: Target file path to lock (or its .lock sidecar when nfs_safe=True).
        timeout: Maximum seconds to wait before raising ``LockTimeoutError``.
        nfs_safe: Use ``<file>.lock`` as the locked file.
        fail_open: If True, return control after ``timeout`` without raising.
        poll_interval: Sleep duration between non-blocking attempts.

    Yields:
        The opened file object kept locked for the duration of the context.
    """
    start = time.time()
    target = Path(file_path)
    lock_target = target.with_suffix(target.suffix + ".lock") if nfs_safe else target
    lock_target.parent.mkdir(parents=True, exist_ok=True)

    mutex = _thread_mutex(lock_target)

    acquired_thread_lock = mutex.acquire(timeout=timeout)
    if not acquired_thread_lock:
        if fail_open:
            yield None
            return
        raise LockTimeoutError(f"Could not acquire lock on {target} within {timeout}s")

    fh = open(lock_target, "a+")
    acquired = False
    try:
        while True:
            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
                break
            except OSError:
                if (time.time() - start) >= timeout:
                    if fail_open:
                        break
                    raise LockTimeoutError(
                        f"Could not acquire lock on {target} within {timeout}s"
                    )
                time.sleep(poll_interval)

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

__all__ = ["acquire_file_lock", "LockTimeoutError"]
